FROM python:3.12-slim AS backend

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY groundtruth/ groundtruth/
COPY config/ config/
COPY data/reference/ data/reference/
COPY data/samples/ data/samples/

FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY groundtruth/ groundtruth/
COPY scripts/ scripts/
COPY config/ config/
COPY data/reference/ data/reference/
COPY data/samples/ data/samples/

COPY --from=frontend-build /app/frontend/dist /app/static

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "groundtruth.api:app", "--host", "0.0.0.0", "--port", "8000"]
