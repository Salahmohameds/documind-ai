# DocuMind AI — frontend

Next.js 16 (App Router) UI for DocuMind AI.

## How the frontend talks to the services

The browser never calls a microservice directly. Every screen goes through one
seam, and that seam calls this app's own route handlers:

```
component ─▶ lib/api.ts ─▶ /api/… (app/api/*) ─▶ document-service
                                              └▶ search-service
```

- **`lib/api.ts`** is the only module a screen imports for data. Each function
  returns exactly the shape the screen renders.
- **`app/api/*/route.ts`** are the backend-for-frontend. They hold the service
  URLs and the service token, normalise every upstream error into one envelope,
  and adapt naming (`search-service` speaks snake_case; the UI contract is
  camelCase).
- **`lib/server/backend.ts`** is the only place a service URL appears.

### Routes

| Route | Backed by | Notes |
|---|---|---|
| `GET /api/documents` | `document-service GET /documents` | Search, filter, sort and pagination are applied in the route — upstream accepts only `page`/`page_size` |
| `POST /api/documents` | `document-service POST /documents` | Multipart passthrough; returns 202 with the queued document |
| `GET /api/documents/[id]` | `document-service GET /documents/{id}` | |
| `GET /api/documents/[id]/status` | `document-service GET /documents/{id}/status` | The cheap poll for in-flight documents |
| `GET /api/documents/counts` | `document-service GET /documents` | Lifecycle counts for the nav badges |
| `GET /api/dashboard` | `document-service GET /documents` | Every metric is derived from real documents |
| `GET /api/search` | `search-service GET /search` | `?q=`, optional `documentId` and `topK` |
| `POST /api/search` | `search-service POST /index` | Chunk, embed and index a document's text |
| `GET /api/health` | both services' `/readiness` | Drives the service-status badge |

## What is real and what is not

Real, end to end: the document library (list, filter, sort, paginate), document
detail, upload with genuine transfer progress, pipeline status polling, library
counts, dashboard metrics, CSV export, semantic indexing and retrieval, and
service health.

Still local, and marked `UNBACKED` in `lib/api.ts`:

- **Sign-in and registration** — `api-gateway` owns `POST /auth/login` and has
  not been built.
- **The document reader's page text** — `processing-service` has not been built,
  so no extracted page content exists.

Where a service exists but has nothing to say (an empty vector index, a document
with no analysis), the UI shows its empty state rather than substituting
fixtures. **Reprocess** and **delete** report as unavailable because
`document-service` defines their schemas but exposes no route.

## Running locally

```bash
cp .env.example .env.local     # then point the URLs at your services
npm install
npm run dev
```

Start the services first — from the repo root:

```bash
docker compose up -d postgres redis search-service
cd services/document-service && uvicorn app.main:app --port 8081
```

`document-service` is not in `docker-compose.yml` yet, so it runs directly. The
upload screen's service badge tells you whether both are reachable.
