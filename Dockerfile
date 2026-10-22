# syntax=docker/dockerfile:1

# ---- 1. build the SPA --------------------------------------------------------
FROM node:22-alpine AS web
WORKDIR /app/frontend
RUN npm install -g pnpm@12.5.1
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
# VITE_* values are public and baked into the bundle at build time.
ARG VITE_API_BASE_URL=""
ARG VITE_MAP_STYLE_URL=""
RUN pnpm build

# ---- 2. python runtime -------------------------------------------------------
FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    APP_ENV=production \
    PORT=8000
RUN pip install --no-cache-dir uv==0.5.4
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
COPY --from=web /app/frontend/dist /app/frontend/dist
RUN SECRET_KEY=build-only ALLOWED_HOSTS=localhost uv run --no-sync python manage.py collectstatic --noinput \
    && useradd --create-home --uid 10001 routeiq
USER routeiq
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/health')"
CMD ["sh", "-c", "exec /app/backend/.venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --threads 4 --timeout 60 --access-logfile -"]
