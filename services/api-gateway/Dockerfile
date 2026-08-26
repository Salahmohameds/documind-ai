# api-gateway Dockerfile
# Multi-stage build, non-root user, minimal final image — per services/README.md

# ── Stage 1: Install dependencies ────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2: Final image ────────────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

# Non-root user (services/README.md: "non-root")
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY . .

RUN chown -R appuser:appuser /app

USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PORT=8000
EXPOSE 8000

# Container-level health check (supplements K8s probes)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/liveness')" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
