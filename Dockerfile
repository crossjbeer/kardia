FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY .env .
COPY . .

RUN pip install --upgrade pip && pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && echo test && uvicorn kardia.app.main:app --host 0.0.0.0 --port 8000"]

