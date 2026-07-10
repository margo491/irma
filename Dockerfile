FROM public.ecr.aws/docker/library/python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS prod
COPY app ./app
COPY alembic.ini .
COPY migrations ./migrations
COPY landing ./landing
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
