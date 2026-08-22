FROM node:22-alpine AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY pyproject.toml ./
COPY backend/ ./backend/
RUN pip install --no-cache-dir ".[online-models]"
COPY --from=frontend-build /build/frontend/dist ./frontend/dist

USER app
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT}"]
