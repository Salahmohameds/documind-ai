# search-service

Semantic search / RAG retrieval layer for DocuMind AI.
Chunks document text, embeds it, stores vectors, and serves top-K similarity
search so the AI Service can generate cited answers.

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/index` | JWT | Chunk + embed + store a document's text |
| POST | `/query` | JWT | Semantic search (JSON body) |
| GET | `/search` | JWT | Semantic search (query params, convenience) |
| GET | `/liveness` | none | k8s liveness probe |
| GET | `/readiness` | none | k8s readiness probe |

### POST /index
```json
// request
{ "document_id": "contract_123", "content": "full text..." }
// or, for page-level citations:
{ "document_id": "contract_123", "content": ["page 1 text", "page 2 text"] }

// response
{ "document_id": "contract_123", "chunks_indexed": 5 }
```

### POST /query
```json
// request
{ "question": "What are the payment terms?", "top_k": 5 }

// response
{
  "question": "What are the payment terms?",
  "results": [
    {
      "chunk_id": "contract_123_chunk_2",
      "document_id": "contract_123",
      "text": "Payment is due within 60 days...",
      "page": 4,
      "similarity": 0.87
    }
  ]
}
```

### GET /search
Same as `/query` but via query params: `/search?question=...&top_k=5`

## Configuration (env vars)

| Var | Default | Notes |
|---|---|---|
| `PORT` | `8080` | HTTP port |
| `EMBEDDING_BACKEND` | `mock` | `mock` \| `local_st` \| `oci` |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | only used by `local_st`/`oci` |
| `EMBEDDING_DIM` | `384` | must match schema.sql's `VECTOR(384)` if changed |
| `VECTOR_STORE_BACKEND` | `memory` | `memory` \| `postgres` |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | - | used when `VECTOR_STORE_BACKEND=postgres` |
| `TOP_K` | `5` | default result count |
| `JWT_SECRET` / `JWT_ALGORITHM` | - | must match API Gateway's signing config |
| `DISABLE_AUTH` | `false` | set `true` for local dev only |

## Running locally

```bash
pip install -r requirements.txt
DISABLE_AUTH=true uvicorn src.main:app --host 0.0.0.0 --port 8080
```

## Running via Docker

```bash
docker build -t search-service:v1 .
docker run -p 8080:8080 -e DISABLE_AUTH=true search-service:v1
```

## Production config (deployment)

```bash
EMBEDDING_BACKEND=oci
VECTOR_STORE_BACKEND=postgres
DB_HOST=<shared postgres service>
JWT_SECRET=<from OCI Vault, matches Gateway's signing key>
```

See `src/embeddings.py::OCIGenerativeAIEmbedder` — one method
(`embed()`) needs the actual OCI Generative AI client wired in; the
interface is already correct.
