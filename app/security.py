"""Password hashing and JWTs.

Two deliberate choices, both explained in module_6:

1. `bcrypt` directly, not `passlib`. passlib's last release was 2020 and it
   cannot drive bcrypt 5.x; every workaround pins one of the two backwards into
   an unmaintained version. The bcrypt package's own API is the four functions
   below.

2. `pyjwt`, not `python-jose`. PyJWT rejects `alg: none` and cross-algorithm
   confusion by default, which is exactly the attack module_6 teaches you to
   defend against.
"""

from __future__ import annotations

import datetime as dt

import bcrypt
import jwt

from app.ports.config import get_settings

settings = get_settings()

# bcrypt hashes at most 72 bytes and raises on anything longer. Silently
# truncating would mean two different long passwords hash identically, so the
# API rejects them instead and says why.
MAX_PASSWORD_BYTES = 72


class PasswordTooLongError(ValueError):
    pass


def hash_password(plain: str) -> str:
    raw = plain.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(
            f"password is {len(raw)} bytes; bcrypt accepts at most {MAX_PASSWORD_BYTES}"
        )
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    raw = plain.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(raw, hashed.encode("utf-8"))


def create_access_token(subject: str, extra: dict | None = None) -> str:
    now = dt.datetime.now(dt.UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.access_token_minutes),
        **(extra or {}),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    # algorithms= is a whitelist, not a hint. Passing the algorithm from the
    # token's own header is the algorithm-confusion vulnerability.
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
