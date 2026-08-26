# DocuMind AI — processing-service
# Multi-stage, non-root, no secrets baked in.
#
# Build the default (Object-Storage-free) image:
#     docker build -t documind/processing-service:dev .
# Build with the OCI SDK for STORAGE_TYPE=oci:
#     docker build --build-arg INSTALL_OCI=true -t documind/processing-service:oci .

# --- Stage 1: build wheels ---------------------------------------------------
FROM python:3.12-slim AS builder

ARG INSTALL_OCI=false

WORKDIR /build

COPY requirements.txt requirements-oci.txt ./

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && if [ "$INSTALL_OCI" = "true" ]; then \
        pip install --no-cache-dir -r requirements-oci.txt; \
    fi

# --- Stage 2: runtime --------------------------------------------------------
FROM python:3.12-slim AS runtime

# Non-root. UID fixed at 10001 to match ai-service, so one PodSecurity policy
# and one runAsUser covers both.
RUN groupadd --gid 10001 documind \
 && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin documind

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

COPY --chown=documind:documind app/ ./app/

# NOTE: /app/storage is deliberately NOT created here.
#
# With STORAGE_TYPE=local, document-service and this service share one volume —
# that service writes it, this one only reads. Docker seeds a fresh named
# volume from the image of whichever container mounts it first, so creating the
# directory here makes the volume's ownership a race: win it, and the uid 10001
# stamped on the volume locks document-service's uid 1000 out of its own
# uploads. A read-only consumer has no business creating that directory at all.
#
# In Kubernetes STORAGE_TYPE=oci and nothing is mounted here. If the directory
# is missing when STORAGE_TYPE=local, the readiness probe reports storage
# unavailable, which is the accurate answer.

USER documind

EXPOSE 8080

# Container-level health check (supplements the K8s probes). Uses /liveness,
# which for this service means "the consumer task is still running" — not
# merely "the HTTP server responds".
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/liveness', timeout=3).status == 200 else 1)" || exit 1

# No secrets, no credentials, no hostnames baked in — everything is env-driven.
# One worker process per container: scaling is the HPA's job, and a second
# uvicorn worker would just be a second consumer sharing one pod's CPU limit.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
