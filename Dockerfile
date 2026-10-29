FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY frontend ./frontend
COPY migrations ./migrations
RUN python -m pip install --no-cache-dir ".[app]"

RUN useradd --create-home --uid 10001 bundlegraph && chown -R bundlegraph:bundlegraph /app
USER bundlegraph
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "bundlegraph_app.main:app", "--host", "0.0.0.0", "--port", "8080"]
