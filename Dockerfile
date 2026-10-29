FROM node:22-alpine AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BUNDLEGRAPH_MIGRATIONS_DIR=/app/migrations \
    BUNDLEGRAPH_FRONTEND_DIRECTORY=/app/frontend
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY migrations ./migrations
COPY --from=frontend-build /frontend/dist ./frontend
RUN python -m pip install --no-cache-dir ".[app]"

RUN useradd --create-home --uid 10001 bundlegraph && chown -R bundlegraph:bundlegraph /app
USER bundlegraph
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "bundlegraph_app.main:app", "--host", "0.0.0.0", "--port", "8080"]
