FROM python:3.11-slim

WORKDIR /app

RUN pip install hatch

COPY backend/pyproject.toml .
RUN pip install .

COPY backend/ .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
