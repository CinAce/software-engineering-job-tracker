import datetime as dt
import io
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from prometheus_client import Counter
from app.events.publisher import publish_event

from app import schemas
from app.auth import current_user
from app.models import User
from app.db import get_db
from app.models import StoredFile
from app.ports.storage import ObjectStore

router = APIRouter(prefix="/files", tags=["files"])

MAX_BYTES = 10 * 1024 * 1024

CONTENT_TYPES = {
    ".csv": "text/csv",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".txt": "text/plain",
}

UPLOADED_BYTES = Counter(
    "itc531_uploaded_bytes_total", 
    "Total bytes uploaded to object storage", 
    ["content_type"]
)

def get_store() -> ObjectStore:
    return ObjectStore()


def content_type_for(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()

    if ext not in CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext or 'no extension'}",
        )

    return CONTENT_TYPES[ext]


def new_key(
    filename: str,
    prefix: str = "uploads",
) -> str:
    ext = os.path.splitext(filename)[1].lower()
    day = dt.datetime.now(dt.UTC).strftime("%Y/%m/%d")

    return f"{prefix}/{day}/{uuid.uuid4()}{ext}"


def read_upload(upload: UploadFile) -> bytes:
    data = upload.file.read(MAX_BYTES + 1)

    if len(data) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File is larger than the 10 MiB limit",
        )

    return data


@router.post(
    "",
    response_model=schemas.StoredFileOut,
    status_code=201,
)
def upload_file(
    file: Annotated[UploadFile, File(...)],
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    original_name = file.filename or "unnamed"
    content_type = content_type_for(original_name)
    data = read_upload(file)
    key = new_key(original_name)
    store = get_store()

    try:
        store.put(
            key=key,
            fileobj=io.BytesIO(data),
            content_type=content_type,
            original_name=original_name,
        )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Object storage is unavailable",
        )

    row = StoredFile(
        owner_id=user.id,
        key=key,
        original_name=original_name,
        content_type=content_type,
        size_bytes=len(data),
    )

    try:
        db.add(row)
        db.commit()
        db.refresh(row)

        UPLOADED_BYTES.labels(content_type=content_type).inc(len(data))
        
        publish_event(
            event_type="resume.uploaded",
            data={
                "file_id": row.id,
                "owner_id": user.id,
                "filename": original_name,
                "size_bytes": len(data)
            }
        )

    except Exception:
        db.rollback()

        try:
            store.delete(key)
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail="Could not save file metadata or publish event",
        )

    return row


@router.post(
    "/multiple",
    response_model=list[schemas.StoredFileOut],
    status_code=201,
)
def upload_multiple_files(
    files: Annotated[list[UploadFile], File(...)],
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    prepared = []

    for file in files:
        original_name = file.filename or "unnamed"
        content_type = content_type_for(original_name)
        data = read_upload(file)

        prepared.append(
            {
                "original_name": original_name,
                "content_type": content_type,
                "data": data,
                "key": new_key(original_name),
            }
        )

    results: list[schemas.StoredFileOut] = []
    store = get_store()

    for item in prepared:
        try:
            store.put(
                key=item["key"],
                fileobj=io.BytesIO(item["data"]),
                content_type=item["content_type"],
                original_name=item["original_name"],
            )

        except Exception:
            raise HTTPException(
                status_code=503,
                detail=f"Could not store {item['original_name']}",
            )

        row = StoredFile(
            owner_id=user.id,
            key=item["key"],
            original_name=item["original_name"],
            content_type=item["content_type"],
            size_bytes=len(item["data"]),
        )

        try:
            db.add(row)
            db.commit()
            db.refresh(row)

            results.append(
                schemas.StoredFileOut.model_validate(row)
            )

        except Exception:
            db.rollback()

            try:
                store.delete(item["key"])
            except Exception:
                pass

            raise HTTPException(
                status_code=500,
                detail=f"Could not save metadata for {item['original_name']}",
            )

    return results


@router.get(
    "",
    response_model=list[schemas.StoredFileOut],
)
def list_files(
    content_type: str | None = None,
    filename: str | None = None,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    statement = select(StoredFile).where(StoredFile.owner_id == user.id)

    if content_type:
        statement = statement.where(
            StoredFile.content_type == content_type
        )

    if filename:
        statement = statement.where(
            StoredFile.original_name.contains(filename)
        )

    statement = (
        statement
        .order_by(StoredFile.id)
        .offset(offset)
        .limit(limit)
    )

    return list(
        db.scalars(statement).all()
    )


@router.get("/download/{file_id}")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    row = db.get(StoredFile, file_id)

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    if row.owner_id != user.id and not any(role.name == 'admin' for role in user.roles):
        raise HTTPException(status_code=403, detail='Forbidden')

    store = get_store()

    try:
        data = store.get(row.key)

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve object from storage",
        )

    return Response(
        content=data,
        media_type=row.content_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{row.original_name}"'
            )
        },
    )


@router.delete(
    "/{file_id}",
    status_code=204,
)
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    row = db.get(StoredFile, file_id)

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    if row.owner_id != user.id and not any(role.name == 'admin' for role in user.roles):
        raise HTTPException(status_code=403, detail='Forbidden')

    store = get_store()

    try:
        store.delete(row.key)

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not delete object from storage",
        )

    try:
        db.delete(row)
        db.commit()

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Object was deleted, but metadata "
                "could not be deleted"
            ),
        )

    return Response(status_code=204)


@router.get("/{file_id}/url")
def presigned_get(
    file_id: int,
    expires_in: int = Query(
        default=900,
        ge=60,
        le=3600,
    ),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    row = db.get(StoredFile, file_id)

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    if row.owner_id != user.id and not any(role.name == 'admin' for role in user.roles):
        raise HTTPException(status_code=403, detail='Forbidden')

    store = get_store()

    try:
        url = store.presigned_get(
            row.key,
            expires_in=expires_in,
        )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not create presigned URL",
        )

    return {
        "url": url,
        "expires_in": expires_in,
    }


@router.post("/presign")
def presigned_put(
    filename: str,
    expires_in: int = Query(
        default=900,
        ge=60,
        le=3600,
    ),
    user: User = Depends(current_user),
):
    content_type = content_type_for(filename)
    key = new_key(
        filename,
        prefix=f"direct/user-{user.id}",
    )

    store = get_store()

    try:
        url = store.presigned_put(
            key,
            content_type=content_type,
            expires_in=expires_in,
        )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not create presigned upload URL",
        )

    return {
        "key": key,
        "url": url,
        "content_type": content_type,
        "expires_in": expires_in,
    }


@router.post("/presign/confirm", response_model=schemas.StoredFileOut)
def confirm_presigned_upload(
    key: str,
    filename: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    expected_prefix = f"direct/user-{user.id}/"

    if not key.startswith(expected_prefix):
        raise HTTPException(
            status_code=403,
            detail="Cannot confirm another user's upload",
        )

    existing = db.scalar(
        select(StoredFile).where(StoredFile.key == key)
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Upload already confirmed",
        )

    store = get_store()

    try:
        metadata = store.head(key)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail="Uploaded object not found",
        )

    row = StoredFile(
        owner_id=user.id,
        key=key,
        original_name=filename,
        content_type=content_type_for(filename),
        size_bytes=metadata["ContentLength"],
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return row