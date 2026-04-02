FROM python:3.11-slim
WORKDIR /app
COPY ../../pyproject.toml ./pyproject.toml
COPY ../../services/shared ./services/shared
COPY . ./services/data-ingestion
RUN pip install --no-cache-dir fastapi pydantic pydantic-settings sqlalchemy asyncpg aiokafka redis uvicorn
ENV PYTHONPATH=/app
CMD ["uvicorn", "services.data-ingestion.main:app", "--host", "0.0.0.0", "--port", "8011"]
