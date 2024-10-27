# embedding_service/Dockerfile
# How to build: from root run the following build
# docker build -t embedding_service:v1.0.0 -f embedding_service/Dockerfile .

FROM python:3.9-slim


# Set work directory
WORKDIR /app

# Install dependencies
COPY embedding_service/app/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/shared_libs/utils \
             /app/shared_libs/config \
             /app/shared_libs/models \
             /app/shared_libs/embeddings

# Copy only the necessary shared_libs modules
COPY shared_libs/shared_libs/utils/logger.py /app/shared_libs/utils/logger.py
COPY shared_libs/shared_libs/config /app/shared_libs/config
COPY shared_libs/shared_libs/embeddings /app/shared_libs/config/embeddings
COPY shared_libs/shared_libs/models/embed_models.py /app/shared_libs/models/embed_models.py

# Copy application code
COPY embedding_service/src/ /app/src/

# Set environment variables (if any)
ENV CONFIG_PATH=/app/shared_libs/config/config.yaml
ENV DOTENV_PATH=/app/shared_libs/config/.env

# Expose port
EXPOSE 8000

# Start the server
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
