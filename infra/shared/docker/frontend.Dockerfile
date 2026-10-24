FROM node:22.14.0-bookworm-slim AS builder
WORKDIR /site
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# These two public values are the only build arguments sent to the browser build.
ARG VITE_SITE_URL
ARG VITE_TURNSTILE_SITE_KEY
RUN npm run build

FROM caddy:2.10.2
COPY --from=builder /site/dist /srv/site
COPY infra/private/Caddyfile /etc/caddy/Caddyfile
