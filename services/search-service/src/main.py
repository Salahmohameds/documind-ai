
import time
import uuid
from typing import List, Optional, Union

import jwt
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import Config
from .instrumentation import (
    configure_logging,
    setup_tracing,
    setup_metrics,
    RequestIDMiddleware,
    get_request_id,
)
from .search import index_document as _index_document, search as _search

SERVICE_NAME = "search-service"

logger = configure_logging(service_name=SERVICE_NAME)

app = FastAPI(title="DocuMind AI - Search Service")

setup_tracing(app, service_name=SERVICE_NAME)
setup_metrics(app)

app.add_middleware(RequestIDMiddleware)

_ready_state = {"ready": False}


# ---------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------

class IndexRequest(BaseModel):
    document_id: str
    content: Union[str, List[str]]  


class IndexResponse(BaseModel):
    document_id: str
    chunks_indexed: int


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    page: Optional[int]
    similarity: float


class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = None


class QueryResponse(BaseModel):
    question: str
    results: List[SearchResultItem]


PUBLIC_PATHS = {"/liveness", "/readiness"}


@app.middleware("http")
async def jwt_auth_middleware(request: Request, call_next):
    if request.url.path in PUBLIC_PATHS or Config.DISABLE_AUTH:
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "Missing bearer token"})

    token = auth_header.split(" ", 1)[1]
    try:
        jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
    except jwt.PyJWTError as e:
        return JSONResponse(status_code=401, content={"error": f"Invalid token: {e}"})

    return await call_next(request)


# ---------------------------------------------------------------------
# Health endpoints (no auth)
# ---------------------------------------------------------------------

@app.get("/liveness")
def liveness():
    """Is the process alive? Always 200 if the server can respond at all."""
    return {"status": "alive"}


@app.get("/readiness")
def readiness():
    """Is the service ready to take traffic? True once embedder/store initialized."""
    if not _ready_state["ready"]:
        # touch the embedder/store once to warm up and verify they work
        try:
            _search.__globals__  # no-op safety
            from .search import _get_embedder, _get_store
            _get_embedder()
            _get_store()
            _ready_state["ready"] = True
        except Exception as e:
            return JSONResponse(status_code=503, content={"status": "not_ready", "error": str(e)})
    return {"status": "ready"}


# ---------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------

@app.post("/index", response_model=IndexResponse)
def index(req: IndexRequest, request: Request):
    request_id = get_request_id()
    try:
        count = _index_document(req.document_id, req.content)
    except Exception as e:
        logger.info(
            "index_failed",
            extra={"request_id": request_id, "document_id": req.document_id},
        )
        raise HTTPException(status_code=500, detail=str(e))

    logger.info(
        "index_completed",
        extra={
            "request_id": request_id,
            "document_id": req.document_id,
        },
    )
    return IndexResponse(document_id=req.document_id, chunks_indexed=count)


def _do_search(question: str, top_k: Optional[int], request_id: str) -> QueryResponse:
    results = _search(question, top_k=top_k)
    logger.info(
        "search_completed",
        extra={"request_id": request_id},
    )
    return QueryResponse(
        question=question,
        results=[
            SearchResultItem(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                text=r.text,
                page=r.page,
                similarity=r.similarity,
            )
            for r in results
        ],
    )


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, request: Request):
    """POST variant - used by internal services (e.g. AI Service) passing a JSON body."""
    return _do_search(req.question, req.top_k, get_request_id())


@app.get("/search", response_model=QueryResponse)
def search_get(question: str, top_k: Optional[int] = None, request: Request = None):
    """GET variant - convenient for quick manual testing / gateway routing."""
    request_id = get_request_id()
    return _do_search(question, top_k, request_id)
