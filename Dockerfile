# Ocean2MQTT : image ghcr.io/ehomelabs/ocean2mqtt
# 1. Interface web (TypeScript / React)
# Build static assets natively once; they are shared by every target architecture.
FROM --platform=$BUILDPLATFORM node:22-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend ./
RUN mkdir -p ../src/ocean2mqtt && npm run build

# 2. Service Python
FROM python:3.13-slim
LABEL org.opencontainers.image.source="https://github.com/eHomeLabs/Ocean2MQTT" \
      org.opencontainers.image.description="Passerelle EnOcean <-> MQTT multi-marques" \
      org.opencontainers.image.licenses="GPL-3.0-only"
WORKDIR /app
COPY pyproject.toml README.md LICENSE LICENSE-MIT.md ./
COPY src ./src
COPY produits ./produits
COPY --from=frontend /build/src/ocean2mqtt/frontend ./src/ocean2mqtt/frontend
RUN pip install --no-cache-dir . && rm -rf /app/src /app/produits
ENV OCEAN2MQTT_DATA=/app/data \
    PYTHONUNBUFFERED=1
VOLUME /app/data
EXPOSE 8080
CMD ["ocean2mqtt"]
