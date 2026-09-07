# Module 1 Tutorial: Cloud Fundamentals and Containerization

By the end of this tutorial you will have written a small FastAPI service, given
it a SQLite database, put it in a container image you wrote the Dockerfile for,
and run that image on your own machine. That image is the same artifact a cloud
provider runs, and everything else in this course is about where you send it.

**You will need:** Rancher Desktop running. Nothing else.

## Learning objectives

- Write a FastAPI service with path and query parameters, and explain how a type
  annotation becomes request validation (SLO 2)
- Persist data with SQLAlchemy models and Pydantic schemas, and say why creating,
  updating and responding need three different shapes (SLO 2)
- Build an image from a Dockerfile you wrote, and predict which source change
  invalidates which layer (SLO 1, SLO 2)
- Explain why the container is the unit this course ships, in terms of what is
  inside the image you built (SLO 1)
- Run that image against a named volume and say which data survives the container
  being destroyed (SLO 2)

<!-- BEGIN PASTE: _shared/setup-block.md with {{MODULE}} = 1 -->

<!-- SHARED BLOCK: preflight. Maintained in _shared/preflight-block.md —
     change it there, not here. {{MODULE}} = 1. -->

> ### Starting here?
>
> **This module assumes nothing from any earlier module.** If this is the first
> one you are doing, or you skipped some, start here:
>
> ```bash
> cd ~/itc531/module_1
> bash scripts/doctor.sh             # confirm your machine and this folder are ready
> docker compose up -d --wait
> ```
>
> `module_1.zip` is attached to this module in Blackboard and is the
> only download you need for it. If you have not set up your machine at all, do
> **Get Ready: Set Up Your Machine** in Blackboard first — about an hour.
>
> This module gets a clean database and clean storage of its own. Nothing carries
> over from another module, and nothing you do here changes what another module
> starts from. Where the text says "as you saw in Module N", that is context, not
> a prerequisite — you can read past it.
>
> **The group project is the exception to all of the above.** Its milestones are
> deliberately cumulative: your team builds one application across the term, and
> Milestone N assumes Milestone N−1. That is what the project is for.

<!-- SHARED BLOCK: setup. Maintained in _shared/setup-block.md —
     change it there, not here. {{MODULE}} = 1. -->

## Setup

Everything in this module runs on your own machine. Nothing here costs money and
nothing leaves your laptop.

Download **`module_1.zip`** from this module in Blackboard and unzip
it. That one file is everything Module 1 needs — you do not need any other
download, and you do not need to have done any earlier module.

```bash
cd ~/itc531/module_1
docker compose up -d --wait
```

That is the whole thing. No flags, no environment variables, no wrapper script.

Docker Compose looks for `compose.yml` in the directory you are standing in, so
the folder you unzipped *is* the module. Open the file — it is worth thirty
seconds:

```bash
cat compose.yml
```

The first line after the comment is `name: itc531m1`. That is the
**project name**, and it is why the modules do not interfere with each other.
Compose prefixes every container, network and volume it creates with it, so
`itc531m2_pgdata` and `itc531m5_pgdata` are different volumes. You can have all
seven modules unzipped side by side, and running at the same time, and none of
them will touch another's database.

`--wait` holds the command until every service reports healthy, so when it
returns the stack is genuinely ready. If it hangs for more than about two
minutes, press Ctrl-C and read the logs:

```bash
docker compose logs -f
```

Every command below runs from this same directory. The ones you will use most:

| Command | What it does |
|---|---|
| `docker compose ps` | What is running, and its health |
| `docker compose logs -f app` | Follow one service's logs |
| `docker compose exec app bash` | A shell inside the running container |
| `docker compose run --rm app python -m pytest -q` | Run the tests |
| `docker compose down --volumes` | Stop it and delete its data |

You do not need to install Python packages. The image already has the course's
pinned dependency set — `requirements.txt`, in this folder.

> **Windows:** use a WSL2 (Ubuntu) terminal, not PowerShell or Git Bash, and keep
> the unzipped folder in your Linux home (`~/itc531`). A folder under `/mnt/c/...`
> breaks file permissions and makes bind mounts slow enough to look broken.
> `bash scripts/doctor.sh` checks both.

## Part 1: A service you wrote
> **Concepts:** Lubanovic Ch 3, *FastAPI Tour*. This Part assumes it.

The stack you started in Setup is the finished course application; leave it
running and do not touch it. What you build is yours. **Stay in the module
folder** — `myapp/` is only where your files live, because the pinned
`requirements.txt` sits in the module folder and a build cannot reach outside the
directory you give it.

```bash
mkdir -p myapp
```

### 1.1 The application

Create `myapp/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(
    title="My First API",
    description="A small FastAPI application",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI", "status": "running"}


@app.get("/hello/{name}")
def say_hello(name: str):
    return {"message": f"Hello, {name}", "name": name}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    result = {"item_id": item_id}
    if q:
        result["query"] = q
    return result


@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

`{name}` and `{item_id}` are **path parameters**, taken from the URL itself; `q`
is a **query parameter**, optional because it has a default. `item_id: int` is not
decoration — FastAPI reads that annotation and rejects a request that does not
supply an integer before your function runs.

### 1.2 Run it

You do not have FastAPI installed and you are not going to install it. Run the
file in a container that has the course's pinned dependencies:

```bash
docker run --rm -it \
  -v "$(pwd)":/code -w /code/myapp \
  -p 8001:8000 \
  python:3.12.11-slim-bookworm \
  sh -c "pip install --quiet --no-cache-dir -r /code/requirements.txt && \
         uvicorn main:app --host 0.0.0.0 --port 8000"
```

`-v "$(pwd)":/code` puts the module folder inside the container, so it runs the
files you are editing and reaches `requirements.txt` at `/code/requirements.txt`;
`-w /code/myapp` is why `main:app` resolves. The host port is 8001 because the
course stack holds 8000. Wait for `Application startup complete`.

### 1.3 Use it

In a second terminal:

```bash
curl http://localhost:8001/
curl http://localhost:8001/hello/Student
curl "http://localhost:8001/items/42?q=search"
curl -i "http://localhost:8001/items/not-a-number"
```

The last request comes back `422 Unprocessable Content`, naming the field and what
was wrong with it: you wrote no validation code, and the annotation was the
validation. Open **http://localhost:8001/docs** to see every endpoint listed with
its parameters and response shape, generated from those same annotations, then
stop the server with Ctrl-C.

## Part 2: Give it a database
> **Concepts:** Lubanovic Ch 5, *Pydantic, Type Hints, and Models Tour*. This
> Part assumes it.

Restarting the service loses everything, because there is nothing but memory.
Three more files fix that: a connection, a table, and the shapes that go in and
out.

### 2.1 The connection

Create `myapp/database.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./tasks.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`check_same_thread` is a SQLite-only setting that lets more than one thread use
the connection, which a web server needs. `get_db` yields a session and closes it
afterwards even if the request raised, which is what makes it usable as a FastAPI
dependency. `DATABASE_URL` writes `tasks.db` into whatever directory the process
is standing in; Part 5 changes that one line.

### 2.2 The table

Create `myapp/models.py`:

```python
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(String)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

One class, one table. `server_default=func.now()` means the database fills
`created_at`, not Python, so it is right even if a row is inserted by something
other than your application.

### 2.3 The shapes

Create `myapp/schemas.py`:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    completed: bool = False


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    completed: bool | None = None


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime | None
```

Three shapes for one table, because they are genuinely different: creating must
not let the caller choose an `id`, updating must let every field be omitted, and
responding must include the `id` and the generated timestamps.
`model_config = ConfigDict(from_attributes=True)` is what lets FastAPI turn a
SQLAlchemy object into this response. This is Pydantic 2 syntax, and the version
matters: Pydantic 2 renamed version 1's `orm_mode` and removed
`Field(regex=...)` in favor of `pattern=`.

## Part 3: The complete task API
> **Concepts:** Lubanovic Ch 6, *Dependencies*. This Part assumes it.

Create `myapp/task_api.py`:

```python
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task Management API", version="1.0.0")


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/tasks", response_model=schemas.TaskResponse, status_code=201)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    row = models.Task(**task.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.get("/tasks", response_model=list[schemas.TaskResponse])
def list_tasks(
    completed: bool | None = None,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(models.Task)
    if completed is not None:
        query = query.filter(models.Task.completed == completed)
    return query.limit(limit).all()


@app.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    row = db.query(models.Task).filter(models.Task.id == task_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return row


@app.patch("/tasks/{task_id}", response_model=schemas.TaskResponse)
def update_task(
    task_id: int, task: schemas.TaskUpdate, db: Session = Depends(get_db)
):
    row = db.query(models.Task).filter(models.Task.id == task_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in task.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    row = db.query(models.Task).filter(models.Task.id == task_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(row)
    db.commit()
```

`Depends(get_db)` is dependency injection: FastAPI calls `get_db`, hands the
handler a session, and runs the cleanup afterwards. `status_code=201` on create
and `204` on delete are the correct codes, and `exclude_unset=True` is what makes
PATCH a partial update instead of writing `None` over every omitted field.
`models.Base.metadata.create_all` creates the table if it is missing and never
alters one that already exists, so editing a model after its table has been
created leaves the table as it was.

Run the command from 1.2 again with `task_api:app` in place of `main:app`, then
exercise all five endpoints from the second terminal:

```bash
curl -i -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Write the Dockerfile", "description": "Part 4"}'

curl http://localhost:8001/tasks
curl http://localhost:8001/tasks/1
curl -X PATCH http://localhost:8001/tasks/1 \
  -H "Content-Type: application/json" -d '{"completed": true}'
curl "http://localhost:8001/tasks?completed=true"
curl -i -X DELETE http://localhost:8001/tasks/1
curl -i http://localhost:8001/tasks/1
```

The last one is `404`, because you just deleted it, and `/docs` now carries the
task endpoints with request and response shapes taken from your Pydantic classes.
Stop the server; `ls -l myapp/tasks.db` shows where the rows went.

## Part 4: Put it in an image
> **Concepts:** Azad Ch 3, *Building and Managing Docker Images*. This Part
> assumes it.

Running with `-v` mounts your source from outside. That is convenient while
writing and it is not how anything ships: an image carries the code, the
interpreter and the dependencies as one artifact, and that artifact is what a
cloud provider runs.

### 4.1 The Dockerfile

Create `myapp/Dockerfile`:

```dockerfile
FROM python:3.12.11-slim-bookworm

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY myapp/ /app

EXPOSE 8000

CMD ["uvicorn", "task_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

`ENV PYTHONUNBUFFERED=1` makes Python write output immediately; without it Python
buffers when stdout is a pipe — which it is, inside a container — and
`docker logs` comes back empty on a healthy process. `--host 0.0.0.0` in the `CMD`
is not optional either: the default binds to loopback inside the container, so you
would map the port correctly and still get connection refused.

### 4.2 Build it

A build cannot reach outside its context, and the context is the last argument to
`docker build`. Give it the module folder — where you already are — and point `-f`
at the Dockerfile, which is what makes `COPY requirements.txt` resolve:

```bash
docker build -f myapp/Dockerfile -t mytaskapi:1.0 .
```

Each instruction is a numbered step producing a **layer**. Run the command again
unchanged and every step says `CACHED`, because Docker reuses a layer when the
instruction and its inputs have not changed. Now edit one line of
`myapp/task_api.py` and build a third time: `COPY myapp/ /app` misses, so it and
everything below it rebuild, while the `pip install` above it stays `CACHED`.
**That is why `requirements.txt` is copied and installed before the source** —
source changes every few minutes, dependencies every few months.

### 4.3 Run the image

```bash
docker run -d --name mytasks -p 8001:8000 mytaskapi:1.0
docker ps
curl http://localhost:8001/health
docker exec -it mytasks ls -l /app
```

No `-v` this time: the code is in the image, and the last command lists the files
that were copied into it from inside the running container.

## Part 5: What survives the container

A container's writable layer is deleted with the container, so a database written
into it goes too. A named volume is storage that outlives the container, and the
process has to write inside it.

Point the database at the directory you are about to mount. Edit
`myapp/database.py` and change one line:

```python
DATABASE_URL = "sqlite:////app/data/tasks.db"
```

Count the slashes: **four**. Three is a relative path, four is absolute, and
`/app/data` is where the volume goes. Rebuild, run with the volume attached,
create a task, then destroy the container and start another one from the same
image and the same volume:

```bash
docker build -f myapp/Dockerfile -t mytaskapi:1.1 .
docker rm -f mytasks
docker volume create taskdata
docker run -d --name mytasks -p 8001:8000 -v taskdata:/app/data mytaskapi:1.1

curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" -d '{"title": "Outlive this container"}'

docker rm -f mytasks
docker run -d --name mytasks -p 8001:8000 -v taskdata:/app/data mytaskapi:1.1
curl http://localhost:8001/tasks
```

The task is there. Data survives only if the process writes inside the volume, so
check `DATABASE_URL` against the mount path that
`docker inspect --format '{{range .Mounts}}{{.Destination}} {{end}}' mytasks`
prints: a volume mounted anywhere else stays empty and nothing errors.

Clean up what you built before the teardown section:

```bash
docker rm -f mytasks
docker volume rm taskdata
docker image rm mytaskapi:1.0 mytaskapi:1.1
```

## Where this runs in the cloud

The image you built in Part 4 is not a rehearsal for a cloud artifact. It **is**
the cloud artifact. The runtime contract is the OCI specification, and it has no
vendor field: a conforming runtime reads the manifest, stacks the layers, applies
the config — your `WORKDIR`, your `EXPOSE`, your `CMD` — and starts the process.
Your laptop implements that contract, and so does every managed container service
you might choose in Module 6.

Three things change when the image moves, and none are inside it: it is stored in
a registry rather than your machine's image store, its environment comes from the
platform rather than a compose file, and its healthcheck is read by something
deciding whether to send you traffic. The application code is not on that list.

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| `Bind for 0.0.0.0:8001 failed: port is already allocated` | Another stack — often a previous module — still holds the port | `bash scripts/stop-all.sh` stops every module's stack. Or find the owner: `docker ps` and `ss -ltn` |
| The container is gone and `docker ps` shows nothing | It started, failed, and exited | `docker ps -a` to find it, then `docker logs <name>` |
| `-p 8001:8000` is mapped, but the port refuses connections | The server bound to loopback inside the container | `--host 0.0.0.0` in the `CMD` |
| Every build reinstalls all dependencies | The source is copied above the install step | Copy `requirements.txt` alone, install, *then* copy source |
| `docker logs` is empty on a running Python container | stdout is block-buffered when it is a pipe | `ENV PYTHONUNBUFFERED=1` |
| `sqlite3.OperationalError: unable to open database file` after the Part 5 edit | The four-slash path names `/app/data`, and nothing is mounted there | Run with `-v taskdata:/app/data` |
| Rows disappear every time the container is replaced | The database file is written outside the mounted volume | Compare `DATABASE_URL` with the volume's mount path |
| `docker: 'compose' is not a docker command` | Compose v1 (`docker-compose`, hyphen) instead of the v2 plugin | Rancher Desktop ships v2. Verify with `docker compose version --short` |
| `bash scripts/doctor.sh` fails with "you are in Git Bash or similar", or on a working directory under `/mnt/c/...` | The shell is MSYS/MinGW rather than WSL2, or the folder is on the Windows drive | Open the Ubuntu terminal from the Start menu, then `cp -r . ~/itc531` and work from there |

## Check yourself

Each of these is answered by running something, not by remembering something.

1. Which layer of `mytaskapi:1.1` is the biggest, and which instruction created
   it? (`docker history mytaskapi:1.1`)
2. Edit only `myapp/task_api.py` and rebuild, then edit `requirements.txt` and
   rebuild. Which steps printed `CACHED` each time, and why is that the argument
   for the order the Dockerfile uses?
3. Send `POST /tasks` with no `title`. What status code comes back, what does the
   body name, and which line of `schemas.py` decided it?
4. Create a task, `docker rm -f` the container, and start it again with
   `-v taskdata:/app/data`. Is the task there? Now start one without `-v`. Explain
   the difference in one sentence about where the process writes.

## Teardown

Run this when you finish, every time. It is one command and it is the habit the
whole course is trying to build.

```bash
docker compose down --volumes
```

`down` stops and removes the containers and the network. `--volumes` also deletes
the data they created, so the next run starts clean and nothing keeps a port or a
gigabyte of disk.

Check nothing is left:

```bash
docker ps                          # should list no itc531 container
docker volume ls | grep itc531     # should print nothing
```

If a module will not start — "port is already allocated", or "address already in
use" — the usual cause is another module still running from a folder you are not
standing in. To stop every module you have unzipped, wherever they are:

```bash
bash scripts/stop-all.sh
```

That script finds every running Compose project whose name begins `itc531m` and
runs the same `docker compose down --volumes` you just ran against each one. Read
it; you will not need it twice.

