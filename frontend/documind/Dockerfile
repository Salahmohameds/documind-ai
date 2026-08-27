# frontend (Next.js 16, App Router) — multi-stage, non-root, minimal final
# image, matching services/README.md's Docker conventions.
#
# Build:
#     docker build -t documind/frontend:dev .
# Run (needs the three backend URLs -- see lib/server/backend.ts):
#     docker run -p 3000:3000 \
#       -e DOCUMENT_SERVICE_URL=http://document-service:8080 \
#       -e SEARCH_SERVICE_URL=http://search-service:8080 \
#       -e AI_SERVICE_URL=http://ai-service:8080 \
#       documind/frontend:dev

# ── Stage 1: install deps ────────────────────────────────────────────────
FROM node:22-slim AS deps
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci

# ── Stage 2: build ────────────────────────────────────────────────────────
FROM node:22-slim AS builder
WORKDIR /build
COPY --from=deps /build/node_modules ./node_modules
COPY . .
# next.config.ts sets output: "standalone" so this produces a minimal
# .next/standalone server instead of requiring the full node_modules tree
# at runtime.
RUN npm run build

# ── Stage 3: runtime ──────────────────────────────────────────────────────
FROM node:22-slim AS runtime
WORKDIR /app

RUN groupadd --gid 10001 nextjs \
 && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin nextjs

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

COPY --from=builder --chown=nextjs:nextjs /build/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /build/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nextjs /build/public ./public

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/api/health', r => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"

CMD ["node", "server.js"]
