FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/chroma

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["sh", "-c", "python -m scripts.seed_db && python -m scripts.ingest_kb && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
