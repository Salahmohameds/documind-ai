# Running DocuMind locally (PowerShell)

Every service defaults to Docker Compose hostnames (`postgres`, `redis`,
`ai-service`, `search-service`) that do not resolve on a Windows host. Running
one by hand therefore means supplying the same environment Compose supplies,
with the hostnames rewritten to `localhost`.

`scripts\run-local.ps1` does all of this in one command and is the recommended
path. This file is the per-service breakdown for when you want to run one
service by itself — a debugger attached, a different port, extra logging.

```powershell
.\scripts\run-local.ps1              # everything
.\scripts\run-local.ps1 -Only gateway,frontend
.\scripts\run-local.ps1 -Status      # what is listening, and is it ready
.\scripts\run-local.ps1 -Stop        # stop what it started
```

## Port map

| Service | Port | Working directory | ASGI app |
|---|---|---|---|
| search-service | 8080 | `services\search-service` | `src.main:app` |
| document-service | 8081 | `services\document-service` | `app.main:app` |
| ai-service | 8082 | `services\ai-service` | `app.main:app` |
| processing-service | 8083 | `services\processing-service` | `app.main:app` |
| api-gateway | 8000 | `services\api-gateway` | `app.main:app` |
| frontend | 3000 | `frontend\documind` | `npm run dev` |
| postgres | 5432 | Docker | — |
| redis | 6379 | Docker | — |

`search-service` is the odd one: its app lives under `src\`, not `app\`.

## Prerequisites

Postgres and Redis run in Docker even when the services do not. Nothing else
starts cleanly without them.

```powershell
cd "D:\Coooding\Cloud Computing\documind-ai"
docker compose up -d postgres redis
docker ps --filter name=documind- --format '{{.Names}}  {{.Status}}'
```

Each service has its own virtualenv at `services\<name>\.venv`. There is also a
shared one at `C:\venvs\documind` used as a fallback. Use the venv's
`python.exe` directly rather than activating — activation does not survive
between tool invocations, and a global `python` will appear to work and then
fail on an import only that venv has.

Shared values used below:

```powershell
$Db      = 'postgresql://documind:documind_dev_only@localhost:5432/documind'
$Redis   = 'redis://localhost:6379/0'
$Storage = 'D:\app\storage'          # document- and processing-service MUST agree
$Jwt     = 'dev-secret-change-me'    # api-gateway issues, search-service validates
```

---

## search-service — port 8080

Retrieval and the vector store. Start it first: processing-service's final
index step calls it.

```powershell
cd "D:\Coooding\Cloud Computing\documind-ai\services\search-service"

$Monitoring = "D:\Coooding\Cloud Computing\documind-ai\services\monitoring"
$env:PYTHONPATH           = "$Monitoring;$Monitoring\app_instrumentation"
$env:PORT                 = '8080'
$env:EMBEDDING_BACKEND    = 'mock'
$env:EMBEDDING_MODEL      = 'all-MiniLM-L6-v2'
$env:EMBEDDING_DIM        = '384'
$env:VECTOR_STORE_BACKEND = 'postgres'
$env:DB_HOST              = 'localhost'
$env:DB_PORT              = '5432'
$env:DB_NAME              = 'documind'
$env:DB_USER              = 'documind'
$env:DB_PASSWORD          = 'documind_dev_only'
$env:DISABLE_AUTH         = 'true'
$env:JWT_SECRET           = 'dev-secret-change-me'

.\.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8080
```

Three of these are load-bearing:

- **`PYTHONPATH`** — `app_instrumentation` (in `services\monitoring`) imports its
  own siblings flat, so both the package parent *and* the package directory have
  to be importable. Omitting this is the whole of the "search-service will not
  start locally" problem.
- **`VECTOR_STORE_BACKEND=postgres`** — the default is `memory`, which loses
  chunks on restart. `document_chunks` stays empty and search and Q&A silently
  return nothing for documents that did index.
- **`DISABLE_AUTH=true`** — api-gateway strips `Authorization` before forwarding
  and mints no downstream credential, so with auth on, gateway → search 401s.

## document-service — port 8081

Owns the `documents` row, uploads, and the analysis read-back.

```powershell
cd "D:\Coooding\Cloud Computing\documind-ai\services\document-service"

$env:PORT              = '8081'
$env:SERVICE_NAME      = 'document-service'
$env:LOG_LEVEL         = 'INFO'
$env:DATABASE_URL      = 'postgresql://documind:documind_dev_only@localhost:5432/documind'
$env:REDIS_URL         = 'redis://localhost:6379/0'
$env:REDIS_STREAM_NAME = 'document_jobs'
$env:STORAGE_TYPE      = 'local'
$env:STORAGE_DIR       = 'D:\app\storage'

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8081
```

`STORAGE_DIR` must match processing-service's. This service writes uploads;
that one reads them back. A mismatch surfaces as "Could not parse the PDF"
rather than as a missing file.

## ai-service — port 8082

Classification, extraction, PII, risk, and answer generation.

```powershell
cd "D:\Coooding\Cloud Computing\documind-ai\services\ai-service"

$env:PORT         = '8082'
$env:SERVICE_NAME = 'ai-service'
$env:LOG_LEVEL    = 'INFO'
$env:PROMPTS_DIR  = 'app\prompts'

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8082
```

Provider credentials come from `services\ai-service\.env`, which is gitignored.
With no `.env` present the service starts in `AI_BACKEND=mock` and serves every
endpoint offline with no credential — see `.env.example` for the shape. This is
also why 8082 rather than 8081: document-service owns 8081, and the frontend's
`DOCUMENT_SERVICE_URL` defaults to it.

## processing-service — port 8083

The pipeline worker. Consumes the `document_jobs` Redis stream, then calls
ai-service and search-service in turn.

```powershell
cd "D:\Coooding\Cloud Computing\documind-ai\services\processing-service"

$env:PORT                 = '8083'
$env:SERVICE_NAME         = 'processing-service'
$env:LOG_LEVEL            = 'INFO'
$env:DATABASE_URL         = 'postgresql://documind:documind_dev_only@localhost:5432/documind'
$env:REDIS_URL            = 'redis://localhost:6379/0'
$env:REDIS_STREAM_NAME    = 'document_jobs'
$env:REDIS_CONSUMER_GROUP = 'processing-workers'
$env:STORAGE_TYPE         = 'local'
$env:STORAGE_DIR          = 'D:\app\storage'
$env:AI_SERVICE_URL       = 'http://localhost:8082'
$env:SEARCH_SERVICE_URL   = 'http://localhost:8080'

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8083
```

**Set `AI_SERVICE_URL` and `SEARCH_SERVICE_URL` together.** With the first set
and the second missing, a document classifies, extracts, scans and scores
successfully and *then* dies at the final index step — after sitting at
`queued` long enough to look like a hung queue. `REDIS_STREAM_NAME` must match
document-service's: producer and consumer agree on the stream by name and
nothing else.

## api-gateway — port 8000

JWT auth and the single front door. Everything the UI needs is mounted here at
the same path the downstream service uses.

```powershell
cd "D:\Coooding\Cloud Computing\documind-ai\services\api-gateway"

$env:PORT                 = '8000'
$env:SERVICE_NAME         = 'api-gateway'
$env:LOG_LEVEL            = 'INFO'
$env:JWT_SECRET           = 'dev-secret-change-me'
$env:SEARCH_SERVICE_URL   = 'http://localhost:8080'
$env:DOCUMENT_SERVICE_URL = 'http://localhost:8081'
$env:AI_SERVICE_URL       = 'http://localhost:8082'

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`JWT_SECRET` must match search-service's — the gateway issues the token, search
validates it.

## frontend — port 3000

```powershell
cd "D:\Coooding\Cloud Computing\documind-ai\frontend\documind"
npm install      # first run only
npm run dev
```

Configured by `frontend\documind\.env.local` (copy `.env.example` if missing).
These are read server-side only; the browser talks exclusively to `/api/...` on
the app's own origin.

```ini
DOCUMIND_API_MODE=gateway
GATEWAY_URL=http://localhost:8000
SEARCH_SERVICE_URL=http://localhost:8080
DOCUMENT_SERVICE_URL=http://localhost:8081
AI_SERVICE_URL=http://localhost:8082
```

`DOCUMIND_API_MODE=direct` bypasses the gateway and calls each service on its
own port — the escape hatch for working on one service in isolation. In direct
mode there is no authentication and no `/qa` endpoint; `/api/qa` falls back to
making the search and answer calls itself.

Sign in at <http://localhost:3000/login> — `admin@documind.com` / `password123`.

---

## Seeding data

`database\seed.sql` loads automatically on a *fresh* Postgres volume. For a
library with realistic filenames and a risk spread across all three bands:

```powershell
Get-Content database\seed_demo.sql -Raw |
  docker exec -i documind-postgres psql -U documind -d documind -v ON_ERROR_STOP=1
```

Idempotent — re-running refreshes the analysis instead of duplicating rows.

## Checking it works

```powershell
# Every service, one line each
8080, 8081, 8082, 8083, 8000 | ForEach-Object {
    $ok = try { (Invoke-WebRequest "http://127.0.0.1:$_/readiness" -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200 }
          catch { $false }
    "{0,-6} {1}" -f $_, $(if ($ok) { 'ready' } else { 'not ready' })
}
```

Every service exposes `GET /liveness` (alive) and `GET /readiness` (ready for
traffic). `readiness` is the one to poll — it checks real dependencies, and it
is what both Compose healthchecks and Kubernetes probes use, so all three agree
on what "up" means.

## Stopping

```powershell
.\scripts\run-local.ps1 -Stop        # services + frontend, by port
docker compose stop postgres redis   # only if you want the data layer down too
```

`-Stop` deliberately leaves Postgres and Redis alone.

## When something is wrong

| Symptom | Cause |
|---|---|
| search-service dies on import | `PYTHONPATH` missing the `monitoring` pair |
| Documents stick at `queued`, never fail | processing-service has `AI_SERVICE_URL` but not `SEARCH_SERVICE_URL` |
| Document indexes, but search and Q&A find nothing | `VECTOR_STORE_BACKEND` left at the `memory` default |
| Gateway → search returns 401 | search-service started without `DISABLE_AUTH=true` |
| "Could not parse the PDF" on a file that uploaded fine | `STORAGE_DIR` differs between document- and processing-service |
| Port already in use | `.\scripts\run-local.ps1 -Status` names the PID holding it |

Uploads and analysis are unaffected by restarting a service — state lives in
Postgres, Redis and `D:\app\storage`, not in any process.
