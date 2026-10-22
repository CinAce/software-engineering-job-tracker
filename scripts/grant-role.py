"""Idempotent role assignment; never expose as an API endpoint."""
import argparse
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Role, User

parser = argparse.ArgumentParser()
parser.add_argument("email")
parser.add_argument("role", choices=["user", "admin"])
args = parser.parse_args()
with SessionLocal() as db:
    user = db.scalar(select(User).where(User.email == args.email))
    if user is None:
        parser.error("register the user first")
    role = db.scalar(select(Role).where(Role.name == args.role))
    if role is None:
        role = Role(name=args.role)
        db.add(role)
        db.flush()
    if role not in user.roles:
        user.roles.append(role)
    db.commit()
    print(f"{user.email}: {role.name} assigned")
