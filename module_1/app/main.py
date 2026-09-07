"""The course application.

One FastAPI app used across all eight modules. Each module's tutorial adds or
exercises a slice of it; nothing is ever thrown away and re-typed.

Health is the endpoint to read first. It reports degraded rather than failing
outright when a dependency is missing, because in modules 1, 4 and 6 several of
these dependencies genuinely are not running, and a health check that lies in
either direction is worse than none.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from prometheus_client import Counter, Histogram, make_asgi_app
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.db import Base, engine, get_db
from app.ports.config import get_settings

settings = get_settings()

REQUESTS = Counter("itc531_requests_total", "Requests", ["method", "path", "status"])
LATENCY = Histogram("itc531_request_seconds", "Request latency", ["method", "path"])


@asynccontextmanager
async def lifespan(_: FastAPI):
    # See Settings.auto_create_tables. From Module 2 onward, migrations own the
    # schema and this is turned off by the compose file, not by editing here.
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,   # never ["*"] — see module 6
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Mounted as a sub-application, so the scrape path is /metrics/ with the
# trailing slash. config/prometheus/prometheus.yml already accounts for this.
app.mount("/metrics", make_asgi_app())

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


@app.middleware("http")
async def observe(request: Request, call_next):
    # The matched route is only in the scope AFTER the router has run, so this
    # must be read after call_next. Reading it before gives None, which falls
    # back to the raw URL — and then /tasks/1, /tasks/2, /tasks/999 each become
    # a separate time series. That is unbounded label cardinality, and it is how
    # a metrics backend gets taken down by a service that looks fine.
    # Module 7 covers this; the fix is one line of ordering.
    start = perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    path = getattr(route, "path", "__unmatched__")
    LATENCY.labels(request.method, path).observe(perf_counter() - start)
    REQUESTS.labels(request.method, path, response.status_code).inc()
    return response


# ------------------------------------------------------------------ health --
@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    checks: dict[str, str] = {}

    try:
        # text() is required. SQLAlchemy 2.x rejects a bare string here, and the
        # resulting ArgumentError makes a working database look broken.
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:                      # noqa: BLE001 - reported, not raised
        checks["database"] = f"unhealthy: {type(exc).__name__}"

    endpoint = os.getenv("S3_ENDPOINT_URL", "")
    if endpoint and "unused" not in endpoint:
        try:
            from app.ports.storage import ObjectStore

            # .list() is a generator, so it does no work until consumed.
            # Pulling one item is what actually exercises the endpoint.
            next(iter(ObjectStore().list()), None)
            checks["storage"] = "ok"
        except Exception as exc:                  # noqa: BLE001
            checks["storage"] = f"unhealthy: {type(exc).__name__}"

    degraded = any(v != "ok" for v in checks.values())
    return {
        "status": "degraded" if degraded else "ok",
        "environment": settings.environment,
        "checks": checks,
    }


@app.get("/")
def root() -> dict:
    return {"service": settings.app_name, "docs": "/docs", "health": "/health"}


# -------------------------------------------------------------------- auth --
def current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    try:
        payload = security.decode_access_token(token)
    except Exception:                              # noqa: BLE001
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from None
    user = db.scalar(select(models.User).where(models.User.email == payload.get("sub")))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown or inactive user")
    return user


@app.post("/auth/register", response_model=schemas.UserOut, status_code=201)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(models.User).where(models.User.email == payload.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    user = models.User(
        email=payload.email, password_hash=security.hash_password(payload.password)
    )
    role = db.scalar(select(models.Role).where(models.Role.name == "user"))
    if role is None:
        role = models.Role(name="user")
        db.add(role)
    user.roles.append(role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == form.username))
    if user is None or not security.verify_password(form.password, user.password_hash):
        # One message for both cases: distinguishing them tells an attacker
        # which addresses are registered.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "incorrect email or password")
    return schemas.TokenOut(access_token=security.create_access_token(user.email))


@app.get("/auth/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(current_user)):
    return user


# ------------------------------------------------------------------- tasks --
@app.post("/tasks", response_model=schemas.TaskOut, status_code=201)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    task = models.Task(title=payload.title)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks", response_model=list[schemas.TaskOut])
def list_tasks(completed: bool | None = None, db: Session = Depends(get_db)):
    stmt = select(models.Task)
    if completed is not None:
        stmt = stmt.where(models.Task.completed == completed)
    return list(db.scalars(stmt))


@app.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    db.delete(task)
    db.commit()
