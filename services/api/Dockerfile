FROM python:3.11-slim

WORKDIR /app

COPY ../../pyproject.toml ./pyproject.toml
COPY ../../services/shared ./services/shared
COPY . ./services/api

RUN pip install --no-cache-dir \
    fastapi>=0.111.0 \
    pydantic>=2.7.0 \
    pydantic-settings>=2.3.0 \
    sqlalchemy>=2.0.0 \
    alembic>=1.13.0 \
    asyncpg>=0.29.0 \
    aiokafka>=0.11.0 \
    redis>=5.0.0 \
    httpx>=0.27.0 \
    uvicorn>=0.29.0 \
    python-jose[cryptography]>=3.3.0 \
    pyotp>=2.9.0 \
    "passlib[bcrypt]>=1.7.4"

ENV PYTHONPATH=/app

CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
