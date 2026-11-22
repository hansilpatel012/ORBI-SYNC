# syntax=docker/dockerfile:1
FROM node:20-alpine AS deps
WORKDIR /app

# Enable pnpm via corepack
RUN corepack enable && corepack prepare pnpm@12.3.4 --activate

# Install dependencies based on pnpm-lock.yaml
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Rebuild the source code only when needed
FROM node:20-alpine AS builder
WORKDIR /app

RUN corepack enable && corepack prepare pnpm@12.3.4 --activate

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Ensure Cesium assets are copied and build production app
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
RUN node scripts/copy-cesium.mjs
RUN pnpm run build

# Production runtime image
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Install curl for healthcheck
RUN apk add --no-cache curl

# Add non-root user for security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application and required assets
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

CMD ["node", "node_modules/next/dist/bin/next", "start", "-p", "3000"]
