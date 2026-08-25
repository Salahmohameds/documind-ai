# search-service Dockerfile
# Multi-stage build, non-root user, minimal final image - per team's Docker conventions

FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

# Non-root user
RUN useradd --create-home --shell /bin/bash appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY . .
RUN chown -R appuser:appuser /app
USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PORT=8080
EXPOSE 8080

# Container-level health check (in addition to k8s probes hitting /liveness)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/liveness')" || exit 1

CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT}"]
