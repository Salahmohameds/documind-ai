# Services — DocuMind AI

> Owners: role 3 (`api-gateway`, `document-service`), role 5 (`processing-service`),
> role 4 (`ai-service`), role 6 (`search-service`).

## Standard service layout

Every service follows the same shape so CI, Docker, and K8s stay uniform:

```text
services/<name>/
├── Dockerfile          # multi-stage, minimal base, non-root
├── README.md           # endpoints, env vars, local run instructions
├── src/                # application code
├── tests/              # unit tests for this service
└── (requirements.txt | pyproject.toml | package.json)
```

## Non-negotiable service contract

| Requirement | Detail |
|-------------|--------|
| Health endpoints | `GET /liveness` (alive) + `GET /readiness` (ready for traffic) — both must check real dependencies where relevant |
| Configuration | 100% from environment variables — no hard-coded hosts, keys, model names |
| Logging | Structured JSON: `timestamp, service, level, request_id, trace_id, event, ...` |
| Tracing | Propagate `traceparent` / `X-Request-ID` headers; export OTel when `OTEL_EXPORTER_OTLP_ENDPOINT` is set |
| Ports | HTTP on `8080` (configurable via `PORT`) |
| Auth | All endpoints behind the gateway JWT except `/liveness`, `/readiness`, and internal metrics |

## API contracts

API contracts (OpenAPI) are defined by the Backend Lead (role 3) in W0 and
live in `docs/architecture/api-contracts/` (or inline per service README).
Other roles code against the contract, not against another service's
implementation.

## Local run

```powershell
docker compose up -d postgres redis
cd services/<name>
# follow the service README (typically: pip install -r requirements.txt && uvicorn app:app --port 8080)
```

## Endpoints overview (from the proposal)

| Service | Key endpoints |
|---------|---------------|
| api-gateway | `POST /auth/login`, proxy `/*` |
| document-service | `POST /documents`, `GET /documents/{id}`, `GET /documents/{id}/status` |
| processing-service | queue consumer; `/liveness`, `/readiness` |
| ai-service | `POST /analysis/risk`, `POST /summarize` |
| search-service | `POST /index`, `POST /query`, `GET /search` |
