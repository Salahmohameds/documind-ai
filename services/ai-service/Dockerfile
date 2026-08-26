# DocuMind AI — ai-service
# Multi-stage, non-root, no secrets baked in.
#
# Build the default (offline-capable) image:
#     docker build -t documind/ai-service:dev .
# Build with the OCI SDK for AI_BACKEND=oci:
#     docker build --build-arg INSTALL_OCI=true -t documind/ai-service:oci .

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

# Non-root. UID is fixed so Kubernetes runAsUser can pin it explicitly.
RUN groupadd --gid 10001 documind \
 && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin documind

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

COPY --chown=documind:documind app/ ./app/

USER documind

EXPOSE 8080

# No secrets, no credentials, no model names baked in — everything is env-driven.
# Prompts ship in the image as a working default but are overridden by the
# ConfigMap mounted at PROMPTS_DIR in Kubernetes.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
