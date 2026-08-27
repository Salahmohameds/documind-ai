# document-service Dockerfile
# Multi-stage build, non-root user, minimal final image — per services/README.md
#
# Build the default (Object-Storage-free) image:
#     docker build -t documind/document-service:dev .
# Build with the OCI SDK for STORAGE_TYPE=oci_object_storage (required in
# Kubernetes — see app/dependencies.py):
#     docker build --build-arg INSTALL_OCI=true -t documind/document-service:oci .

# ── Stage 1: Install dependencies ────────────────────────────────────────
FROM python:3.11-slim AS builder

ARG INSTALL_OCI=false

WORKDIR /build
COPY requirements.txt requirements-oci.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt \
 && if [ "$INSTALL_OCI" = "true" ]; then \
        pip install --no-cache-dir --user -r requirements-oci.txt; \
    fi

# ── Stage 2: Final image ────────────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

# Non-root user (services/README.md: "non-root")
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY . .

# Create the local-storage directory the service writes uploads to.
# Owned by appuser so the non-root process can write.
RUN mkdir -p /app/storage && chown -R appuser:appuser /app

USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PORT=8080
EXPOSE 8080

# Container-level health check (supplements K8s probes)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/liveness')" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
