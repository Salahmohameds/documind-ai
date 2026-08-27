<#
.SYNOPSIS
    Starts the whole DocuMind stack on Windows, outside Docker Compose.

.DESCRIPTION
    Every service defaults to Compose service names (postgres, redis,
    ai-service, search-service) that do not resolve on a host. Running them by
    hand therefore means supplying the same environment Compose supplies, with
    the hostnames rewritten to localhost -- and getting one of them wrong
    produces a failure that looks like something else entirely. The known trap:
    processing-service with AI_SERVICE_URL set but SEARCH_SERVICE_URL missing
    classifies, extracts, scans and scores a document successfully and then
    dies at the final index step, after leaving the document sitting at
    "queued" long enough to look like a hung queue.

    This script is the single source of truth for that environment. Each
    service opens in its own window so its logs stay readable and Ctrl+C stops
    one without stopping the rest.

.PARAMETER Only
    Start just these services. Names: search, document, ai, processing,
    gateway, frontend.

.PARAMETER Stop
    Stop everything this script started (matched by port) and exit.

.PARAMETER Status
    Print what is listening and each service's readiness, then exit.

.EXAMPLE
    .\scripts\run-local.ps1
    .\scripts\run-local.ps1 -Status
    .\scripts\run-local.ps1 -Only gateway,frontend
    .\scripts\run-local.ps1 -Stop
#>

[CmdletBinding()]
param(
    [ValidateSet('search', 'document', 'ai', 'processing', 'gateway', 'frontend')]
    [string[]] $Only,
    [switch] $Stop,
    [switch] $Status
)

$ErrorActionPreference = 'Stop'

# Repo root, derived from this script rather than the caller's location.
$Root = Split-Path -Parent $PSScriptRoot
$Services = Join-Path $Root 'services'

# ---------------------------------------------------------------------------
# Shared configuration
# ---------------------------------------------------------------------------

# Matches docker-compose.yml. Postgres and Redis still run in Docker.
$DbUrl    = 'postgresql://documind:documind_dev_only@localhost:5432/documind'
$RedisUrl = 'redis://localhost:6379/0'

# document-service writes uploads here and processing-service reads them back.
# They MUST agree: a mismatch surfaces as "Could not parse the PDF" rather than
# as a missing file. This is the Windows resolution of the container default
# (/app/storage), which is where the existing uploads already are.
$StorageDir = 'D:\app\storage'

# HS256 secret shared by api-gateway (issues tokens) and search-service
# (validates them). Dev value only.
$JwtSecret = 'dev-secret-change-me'

# `app_instrumentation` lives in services/monitoring and imports its own
# siblings flat (`from request_id_middleware import ...`), so BOTH the package
# parent and the package directory have to be importable. This is the whole of
# the "search-service will not start locally" problem.
$Monitoring = Join-Path $Services 'monitoring'
$PyPath     = "$Monitoring;$(Join-Path $Monitoring 'app_instrumentation')"

# ---------------------------------------------------------------------------
# Service table -- port, working directory, interpreter, ASGI app, environment
# ---------------------------------------------------------------------------

$Plan = [ordered]@{
    search = @{
        Port = 8080
        Cwd  = Join-Path $Services 'search-service'
        App  = 'src.main:app'
        Env  = @{
            PORT                 = '8080'
            EMBEDDING_BACKEND    = 'mock'
            EMBEDDING_MODEL      = 'all-MiniLM-L6-v2'
            EMBEDDING_DIM        = '384'
            # `memory` is the default and it is the wrong one here: chunks are
            # lost on restart and document_chunks stays empty, so search and
            # Q&A silently return nothing for documents that did index.
            VECTOR_STORE_BACKEND = 'postgres'
            DB_HOST              = 'localhost'
            DB_PORT              = '5432'
            DB_NAME              = 'documind'
            # Defaults are postgres/postgres, which is not this project's user.
            DB_USER              = 'documind'
            DB_PASSWORD          = 'documind_dev_only'
            # api-gateway strips Authorization before forwarding and mints no
            # downstream credential, so with auth on, Gateway -> search 401s.
            DISABLE_AUTH         = 'true'
            JWT_SECRET           = $JwtSecret
            PYTHONPATH           = $PyPath
        }
    }
    document = @{
        Port = 8081
        Cwd  = Join-Path $Services 'document-service'
        App  = 'app.main:app'
        Env  = @{
            PORT              = '8081'
            SERVICE_NAME      = 'document-service'
            LOG_LEVEL         = 'INFO'
            DATABASE_URL      = $DbUrl
            REDIS_URL         = $RedisUrl
            REDIS_STREAM_NAME = 'document_jobs'
            STORAGE_TYPE      = 'local'
            STORAGE_DIR       = $StorageDir
        }
    }
    ai = @{
        Port = 8082
        Cwd  = Join-Path $Services 'ai-service'
        App  = 'app.main:app'
        Env  = @{
            PORT         = '8082'
            SERVICE_NAME = 'ai-service'
            LOG_LEVEL    = 'INFO'
            PROMPTS_DIR  = 'app/prompts'
            # Reads services/ai-service/.env if present for a real provider
            # key; with none it starts in AI_BACKEND=mock and still serves
            # every endpoint offline.
        }
    }
    processing = @{
        Port = 8083
        Cwd  = Join-Path $Services 'processing-service'
        App  = 'app.main:app'
        Env  = @{
            PORT                 = '8083'
            SERVICE_NAME         = 'processing-service'
            LOG_LEVEL            = 'INFO'
            DATABASE_URL         = $DbUrl
            REDIS_URL            = $RedisUrl
            # Producer and consumer agree on the stream by name and nothing
            # else -- this must match document-service's REDIS_STREAM_NAME.
            REDIS_STREAM_NAME    = 'document_jobs'
            REDIS_CONSUMER_GROUP = 'processing-workers'
            STORAGE_TYPE         = 'local'
            STORAGE_DIR          = $StorageDir
            # The pair that must both be set. See the note at the top.
            AI_SERVICE_URL       = 'http://localhost:8082'
            SEARCH_SERVICE_URL   = 'http://localhost:8080'
        }
    }
    gateway = @{
        Port = 8000
        Cwd  = Join-Path $Services 'api-gateway'
        App  = 'app.main:app'
        Env  = @{
            PORT                 = '8000'
            SERVICE_NAME         = 'api-gateway'
            LOG_LEVEL            = 'INFO'
            JWT_SECRET           = $JwtSecret
            SEARCH_SERVICE_URL   = 'http://localhost:8080'
            DOCUMENT_SERVICE_URL = 'http://localhost:8081'
            AI_SERVICE_URL       = 'http://localhost:8082'
        }
    }
}

$FrontendPort = 3000
$FrontendDir  = Join-Path $Root 'frontend\documind'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Get-Interpreter {
    param([string] $ServiceDir)

    # Each service has its own .venv except processing-service, which uses the
    # shared one. Falling back to a global python would appear to work and then
    # fail on an import that only that venv has.
    $own = Join-Path $ServiceDir '.venv\Scripts\python.exe'
    if (Test-Path $own) { return $own }

    $shared = 'C:\venvs\documind\Scripts\python.exe'
    if (Test-Path $shared) { return $shared }

    throw "No interpreter for $ServiceDir (looked for .venv, then C:\venvs\documind)."
}

function Get-ListenerPid {
    param([int] $Port)
    $c = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
         Select-Object -First 1
    if ($c) { return $c.OwningProcess }
    return $null
}

function Test-Ready {
    param([int] $Port)
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/readiness" `
                               -TimeoutSec 4 -UseBasicParsing
        return $r.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Start-ServiceWindow {
    param(
        [string] $Name,
        [hashtable] $Spec
    )

    $existing = Get-ListenerPid -Port $Spec.Port
    if ($existing) {
        Write-Host ("  {0,-11} port {1} already in use (pid {2}) - skipped" -f $Name, $Spec.Port, $existing) -ForegroundColor Yellow
        return
    }

    $python = Get-Interpreter -ServiceDir $Spec.Cwd

    # Env assignments, then uvicorn, run inside the new window. Passed as one
    # -Command string so the variables are set in the same session that starts
    # the server.
    $sets = ($Spec.Env.GetEnumerator() | ForEach-Object {
        "`$env:$($_.Key)='$($_.Value)'"
    }) -join '; '

    $inner = "$sets; Write-Host '=== $Name :$($Spec.Port) ===' -ForegroundColor Cyan; " +
             "& '$python' -m uvicorn $($Spec.App) --host 127.0.0.1 --port $($Spec.Port)"

    Start-Process powershell -WorkingDirectory $Spec.Cwd -ArgumentList @(
        '-NoExit', '-NoProfile', '-Command', $inner
    ) | Out-Null

    Write-Host ("  {0,-11} starting on {1}" -f $Name, $Spec.Port) -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# -Status
# ---------------------------------------------------------------------------

if ($Status) {
    Write-Host "`nDocuMind - local stack`n" -ForegroundColor Cyan
    foreach ($name in $Plan.Keys) {
        $port = $Plan[$name].Port
        $procId = Get-ListenerPid -Port $port
        $state = if (-not $procId) { 'stopped' }
                 elseif (Test-Ready -Port $port) { 'ready' }
                 else { 'listening (not ready)' }
        "{0,-11} {1,-6} {2}" -f $name, $port, $state | Write-Host
    }
    $fePid = Get-ListenerPid -Port $FrontendPort
    "{0,-11} {1,-6} {2}" -f 'frontend', $FrontendPort, $(if ($fePid) { 'running' } else { 'stopped' }) | Write-Host

    Write-Host "`nDocker:" -ForegroundColor Cyan
    docker ps --filter 'name=documind-' --format '  {{.Names}}  {{.Status}}'
    Write-Host ''
    exit 0
}

# ---------------------------------------------------------------------------
# -Stop
# ---------------------------------------------------------------------------

if ($Stop) {
    Write-Host "`nStopping local services (Postgres and Redis are left alone)`n" -ForegroundColor Cyan
    $ports = @($Plan.Keys | ForEach-Object { $Plan[$_].Port }) + $FrontendPort
    foreach ($port in $ports) {
        $procId = Get-ListenerPid -Port $port
        if ($procId) {
            Stop-Process -Id $procId -Force -Confirm:$false -ErrorAction SilentlyContinue
            Write-Host ("  port {0,-6} stopped (pid {1})" -f $port, $procId) -ForegroundColor Green
        }
    }
    Write-Host ''
    exit 0
}

# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

Write-Host "`nDocuMind - starting local stack`n" -ForegroundColor Cyan

# Postgres and Redis are prerequisites, not things this script owns.
$running = @(docker ps --filter 'name=documind-' --format '{{.Names}}')
foreach ($need in 'documind-postgres', 'documind-redis') {
    if ($running -notcontains $need) {
        Write-Host "  $need is not running. Start it with:" -ForegroundColor Red
        Write-Host "    docker compose up -d postgres redis`n" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  postgres + redis  ok (docker)" -ForegroundColor DarkGray

if (-not (Test-Path $StorageDir)) {
    New-Item -ItemType Directory -Force -Path $StorageDir | Out-Null
    Write-Host "  created $StorageDir" -ForegroundColor DarkGray
}

$wanted = if ($Only) { $Only } else { @($Plan.Keys) + 'frontend' }

# Start order matters only in that the Gateway and processing-service log
# connection errors until their dependencies answer; both recover on their own.
foreach ($name in $Plan.Keys) {
    if ($wanted -contains $name) { Start-ServiceWindow -Name $name -Spec $Plan[$name] }
}

if ($wanted -contains 'frontend') {
    $existing = Get-ListenerPid -Port $FrontendPort
    if ($existing) {
        Write-Host ("  {0,-11} port {1} already in use (pid {2}) - skipped" -f 'frontend', $FrontendPort, $existing) -ForegroundColor Yellow
    } else {
        Start-Process powershell -WorkingDirectory $FrontendDir -ArgumentList @(
            '-NoExit', '-NoProfile', '-Command',
            "Write-Host '=== frontend :$FrontendPort ===' -ForegroundColor Cyan; npm run dev"
        ) | Out-Null
        Write-Host ("  {0,-11} starting on {1}" -f 'frontend', $FrontendPort) -ForegroundColor Green
    }
}

Write-Host "`n  Sign in at http://localhost:$FrontendPort/login  (admin@documind.com / password123)"
Write-Host "  Check with: .\scripts\run-local.ps1 -Status`n"
