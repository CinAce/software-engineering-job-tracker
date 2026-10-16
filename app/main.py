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
import json
import uuid
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app
from sqlalchemy import select, text
from sqlalchemy.orm import Session
import pika
import pika.exceptions

from app import models, schemas, security
from app.auth import current_user
from app.db import Base, engine, get_db
from app.files import router as files_router
from app.ports.config import get_settings

settings = get_settings()

REQUESTS = Counter("itc531_requests_total", "Requests", ["method", "path", "status"])
LATENCY = Histogram("itc531_request_seconds", "Request latency", ["method", "path"])


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.mount("/metrics", make_asgi_app())


@app.middleware("http")
async def observe(request: Request, call_next):
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
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"unhealthy: {type(exc).__name__}"

    endpoint = os.getenv("S3_ENDPOINT_URL", "")
    if endpoint and "unused" not in endpoint:
        try:
            from app.ports.storage import ObjectStore

            next(iter(ObjectStore().list()), None)
            checks["storage"] = "ok"
        except Exception as exc:
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
    # DEMO ONLY: missing users skip bcrypt, so response timing may differ.
    if user is None or not security.verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "incorrect email or password")
    return schemas.TokenOut(access_token=security.create_access_token(user.email))


@app.get("/auth/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(current_user)):
    return user


def require_role(role_name: str):
    """Reusable role requirement, chained to token authentication."""
    def dependency(user: models.User = Depends(current_user)) -> models.User:
        if not any(role.name == role_name for role in user.roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient permissions")
        return user
    return dependency


def task_access(task: models.Task, user: models.User) -> None:
    if task.owner_id != user.id and not any(r.name == "admin" for r in user.roles):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not task owner")


@app.get("/admin/tasks", response_model=list[schemas.TaskOut])
def admin_tasks(db: Session = Depends(get_db), _: models.User = Depends(require_role("admin"))):
    return list(db.scalars(select(models.Task).order_by(models.Task.id)))


app.include_router(files_router, dependencies=[Depends(current_user)])

# ------------------------------------------------------------------- tasks --
@app.post("/tasks", response_model=schemas.TaskOut, status_code=201)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    task = models.Task(title=payload.title, owner_id=user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks", response_model=list[schemas.TaskOut])
def list_tasks(completed: bool | None = None, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    stmt = select(models.Task).where(models.Task.owner_id == user.id)
    if completed is not None:
        stmt = stmt.where(models.Task.completed == completed)
    return list(db.scalars(stmt))


@app.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    task_access(task, user)
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    task_access(task, user)
    db.delete(task)
    db.commit()


# ------------------------------------------------------------------ queues --
class ScrapeRequest(BaseModel):
    url: str = Field(min_length=8, pattern=r"^https?://")
    job_id: int = Field(gt=0)


class ExportRequest(BaseModel):
    user_id: int = Field(gt=0)


def get_broker_connection():
    broker_url = os.environ.get("BROKER_URL")
    try:
        parameters = pika.URLParameters(broker_url)
        return pika.BlockingConnection(parameters)
    except pika.exceptions.AMQPConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Message broker is currently unavailable",
        )


@app.post("/api/jobs/scrape", status_code=status.HTTP_202_ACCEPTED)
def trigger_scrape(request: ScrapeRequest, _: models.User = Depends(current_user)):
    task_id = str(uuid.uuid4())
    connection = get_broker_connection()
    channel = connection.channel()
    channel.queue_declare(queue="scrape_queue", durable=True)

    message = {"id": task_id, "url": request.url, "job_id": request.job_id}
    channel.basic_publish(
        exchange="",
        routing_key="scrape_queue",
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=pika.DeliveryMode.Persistent
        ),
    )
    connection.close()
    return {"id": task_id, "status": "accepted", "workflow": "scrape"}


@app.post("/api/exports", status_code=status.HTTP_202_ACCEPTED)
def trigger_export(request: ExportRequest, user: models.User = Depends(current_user)):
    if request.user_id != user.id and not any(r.name == "admin" for r in user.roles):
        raise HTTPException(403, "cannot export another user")
    task_id = str(uuid.uuid4())
    connection = get_broker_connection()
    channel = connection.channel()
    channel.queue_declare(queue="export_queue", durable=True)

    message = {"id": task_id, "user_id": request.user_id}
    channel.basic_publish(
        exchange="",
        routing_key="export_queue",
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=pika.DeliveryMode.Persistent
        ),
    )
    connection.close()
    return {"id": task_id, "status": "accepted", "workflow": "export"}


class EventPublishRequest(BaseModel):
    event_type: str = Field(min_length=1)
    data: dict = Field(min_length=1)


@app.post("/api/events/publish", status_code=status.HTTP_202_ACCEPTED)
def publish_domain_event(request: EventPublishRequest, _: models.User = Depends(require_role("admin"))):
    from app.events.publisher import publish_event

    try:
        event = publish_event(
            event_type=request.event_type,
            data=request.data,
        )

        return {
            "status": "published",
            "event": event,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except pika.exceptions.AMQPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Message broker is currently unavailable",
        )