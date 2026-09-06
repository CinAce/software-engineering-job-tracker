FROM python:3.12.11-slim-bookworm
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY myapp/ /app
EXPOSE 8000
CMD ["uvicorn", "task_api:app", "--host", "0.0.0.0", "--port", "8000"]
