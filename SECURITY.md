# Milestone 5 security notes (partial implementation)

Register with `POST /auth/register` using JSON `{"email":"student@example.edu","password":"long-password-here"}`. Login at `POST /auth/login` using form fields `username` and `password`; send `Authorization: Bearer <access_token>` to `/auth/me` and protected routes. The JWT expires after 30 minutes by default. Passwords are bcrypt hashes (cost 12, chosen 2026), not plaintext. A 72-character schema limit is distinct from bcrypt's 72-*byte* UTF-8 limit; both are checked to prevent silent truncation.

## Roles and ownership

Users get `user` on registration; `admin` can be assigned only through `python scripts/grant-role.py EMAIL admin`. Roles are many-to-many. Ordinary users create/list their own tasks and may read/delete only owned tasks. Admins can read/delete any task and list `/admin/tasks`. Authentication failures are 401 (identity missing or invalid); authorization failures are 403 (identity known but action forbidden).

## Deliberately public endpoints

`/`, `/health`, `/auth/register`, `/auth/login`, `/docs`, `/openapi.json`, and `/metrics/` remain public. **Before production, restrict health detail, docs and metrics at the gateway.**

## Demo-only limitations and pre-deployment checklist

- `app/main.py`: login's missing-user branch skips bcrypt; timing is not equalized (marked DEMO ONLY inline).
- `app/ports/config.py`: local auto-create-tables and local CORS defaults must be reviewed before deployment.
- File routes require a token, but **file ownership is not yet enforced**; add `StoredFile.owner_id`, migrate existing rows, and check ownership on read/delete/URL before exposing this API.
- Ensure all persistent databases receive a migration adding `tasks.owner_id`; `create_all()` does not alter existing tables.
- Confirm all request bodies have constraints, audit every public endpoint, add rate limits, rotate secrets, restrict CORS and metrics, and run attack tests.
- Never deploy with a default JWT secret. `.env` must be ignored and `.env.example` contains placeholders only. SQL queries use SQLAlchemy ORM or fixed parameterized text.
