import time
import random
from fastapi import FastAPI, HTTPException

################# NECESSARY IMPORTS
from opentelemetry import trace
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from app_instrumentation.logging_setup import configure_logging
from app_instrumentation.otel_setup import setup_tracing, setup_metrics
from app_instrumentation.request_id_middleware import RequestIDMiddleware, get_request_id
#################

SERVICE_NAME = "sample-service"

app = FastAPI()

################# THIS IS THE PART YOU ADD IN YOUR FASTAPI SERVER.
logger = configure_logging(service_name=SERVICE_NAME)
setup_tracing(app, service_name=SERVICE_NAME)
setup_metrics(app)
app.add_middleware(RequestIDMiddleware)
RequestsInstrumentor().instrument()
#################


################# THE BELOW CODE ARE SAMPLE ENDPOINTS FOR TESTING.
@app.get("/")
def root():
    logger.info("root endpoint hit")
    return {"service": SERVICE_NAME, "request_id": get_request_id()}


@app.get("/documents/{document_id}")
def get_document(document_id: str):
    logger.info("fetching document", extra={"document_id": document_id})

    time.sleep(random.uniform(0.05, 0.3))

    logger.info("document found", extra={"document_id": document_id})
    return {"document_id": document_id, "status": "processed"}


@app.get("/fail")
def fail():
    """Hit this a few times to see the Error Rate panel and error logs populate."""
    logger.error("simulated failure triggered")
    raise HTTPException(status_code=500, detail="simulated failure")


@app.get("/health")
def health():
    return {"status": "ok"}
#################