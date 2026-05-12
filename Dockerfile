FROM node:24-bookworm-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package.json ./package.json
RUN npm install --include=dev --no-audit --no-fund

COPY frontend ./frontend
WORKDIR /frontend/frontend
RUN npx tsc -b && npx vite build

FROM python:3.12.4

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-build /frontend/static/spa /app/static/spa

CMD ["gunicorn", "project_config.wsgi:application", "--bind", "0.0.0.0:8000"]
