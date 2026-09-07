"""Pydantic v2 schemas.

Note `pattern=` rather than `regex=`. `regex=` was removed in Pydantic 2.0; a
schema that still uses it raises PydanticUserError at import, so the application
does not start at all. That defect shipped in the previous version of this
course.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    is_active: bool
    created_at: dt.datetime
    # RoleOut, not str. The ORM relationship returns Role objects; declaring
    # list[str] makes every successful response fail serialization with a 500.
    roles: list[RoleOut] = []


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    completed: bool
    created_at: dt.datetime


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=100)
    isbn: str = Field(pattern=r"^\d{3}-\d{10}$")
    price: float = Field(gt=0)


class StoredFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    original_name: str
    content_type: str
    size_bytes: int
    uploaded_at: dt.datetime
