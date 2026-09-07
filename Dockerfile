# ITC 531 application image.
#
# Multi-stage: the builder installs dependencies, the runtime carries only what
# is needed to run. Week 7 takes this apart in detail; weeks 1-6 just use it.

ARG PYTHON_TAG=3.12.11-slim-bookworm

# ---------------------------------------------------------------- builder ---
FROM python:${PYTHON_TAG} AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY requirements.txt .

# --prefix keeps everything in one relocatable tree, which the runtime stage
# copies to a real site-packages location. This avoids the classic broken
# multi-stage image where files land in /root/.local and the non-root runtime
# user cannot import them.
RUN pip install --prefix=/install -r requirements.txt

# ---------------------------------------------------------------- runtime ---
FROM python:${PYTHON_TAG} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:${PATH}"

# curl is genuinely needed: the HEALTHCHECK below uses it, and the slim base
# does not ship it. An image whose healthcheck binary is missing reports
# unhealthy forever, which is a real defect and not a hypothetical one.
RUN apt-get update \
 && apt-get install --no-install-recommends -y curl \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 appuser

# /data is where a SQLite-backed week's compose.yml mounts a named volume
# (week 1, week 6). Docker copies an image directory's ownership into a named
# volume the first time it is mounted there, but only if the directory already
# exists in the image with the right owner -- otherwise the volume is created
# root:root and the non-root USER below can never open a database file in it.
RUN mkdir -p /data && chown appuser:appuser /data

COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=appuser:appuser app/       ./app/
COPY --chown=appuser:appuser functions/ ./functions/
COPY --chown=appuser:appuser tests/     ./tests/
# migrations/ is created by the student in Module 2 and bind-mounted by
# compose.week2.yml, so it is deliberately not baked into the image.

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

# One worker by default. Week 7 explains when and why to raise it — briefly:
# each uvicorn worker is a full Python process at roughly 100-150 MB, so four
# of them inside a 1 GB container limit is how you get an OOM kill that looks
# like a mysterious restart loop.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
