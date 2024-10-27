# embedding_service/Dockerfile.worker
# How to build: from root run the following build
# docker build -t embedding_service:v1.0.0 -f embedding_service/Dockerfile .

FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies
COPY embedding_service/app/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY embedding_service/app/ /app/app/

# Copy shared_libs modules
COPY shared_libs/shared_libs/utils/logger.py /app/shared_libs/utils/logger.py
COPY shared_libs/shared_libs/config/config_loader.py /app/shared_libs/config/config_loader.py
COPY shared_libs/shared_libs/config/config.yaml /app/shared_libs/config/config.yaml
COPY shared_libs/shared_libs/config/.env /app/shared_libs/config/.env

# Set environment variables (if any)
ENV CONFIG_PATH=/app/shared_libs/config/config.yaml
ENV DOTENV_PATH=/app/shared_libs/config/.env

# Expose port
EXPOSE 8000

# Start the server
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
