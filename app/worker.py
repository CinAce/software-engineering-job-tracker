from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import pika
import pika.exceptions
import os
import json
import uuid

app = FastAPI(title="Software Engineering Job Tracker API")

class ScrapeRequest(BaseModel):
    url: str
    job_id: int

class ExportRequest(BaseModel):
    user_id: int

def get_broker_connection():
    broker_url = os.environ.get("BROKER_URL")
    try:
        parameters = pika.URLParameters(broker_url)
        return pika.BlockingConnection(parameters)
    except pika.exceptions.AMQPConnectionError:
        # Returns 503 if the broker is unreachable, as required
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Message broker is currently unavailable"
        )

@app.get("/health")
def health_check():
    return {"status": "api healthy"}

@app.post("/api/jobs/scrape", status_code=status.HTTP_202_ACCEPTED)
def trigger_scrape(request: ScrapeRequest):
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
            delivery_mode=pika.DeliveryMode.Persistent # Enforces message durability
        )
    )
    connection.close()
    return {"id": task_id, "status": "accepted", "workflow": "scrape"}

@app.post("/api/exports", status_code=status.HTTP_202_ACCEPTED)
def trigger_export(request: ExportRequest):
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
            delivery_mode=pika.DeliveryMode.Persistent # Enforces message durability
        )
    )
    connection.close()
    return {"id": task_id, "status": "accepted", "workflow": "export"}