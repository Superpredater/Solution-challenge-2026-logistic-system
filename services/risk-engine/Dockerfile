FROM python:3.11-slim
WORKDIR /app
COPY ../../pyproject.toml ./pyproject.toml
COPY ../../services/shared ./services/shared
COPY . ./services/risk-engine
RUN pip install --no-cache-dir fastapi pydantic pydantic-settings sqlalchemy asyncpg aiokafka redis uvicorn
ENV PYTHONPATH=/app
CMD ["python", "-m", "services.risk-engine.main"]
