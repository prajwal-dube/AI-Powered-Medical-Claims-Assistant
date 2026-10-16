FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
COPY claims_assistant ./claims_assistant
RUN pip install --no-cache-dir ".[dashboard]"
COPY dashboard.py ./
COPY scripts ./scripts
ENV DATABASE_PATH=/data/claims.db EXTRACTOR_MODE=demo
RUN mkdir -p /data
EXPOSE 8000
CMD ["uvicorn", "claims_assistant.main:app", "--host", "0.0.0.0", "--port", "8000"]
