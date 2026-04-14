# Build from repository root (e.g. `docker build -t api .`).
# Backend app lives in ./backend; this file exists so hosts that expect a root Dockerfile can build the API.
FROM python:3.11-slim

WORKDIR /app

RUN pip install hatch

COPY backend/pyproject.toml .
RUN pip install .

COPY backend/ .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
