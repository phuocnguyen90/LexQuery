# Dockerfile in root directory

# Use an official Python runtime as the base image
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY rag_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install fastembed separately
RUN pip install fastembed

# Copy shared_libs and install it
COPY shared_libs /app/shared_libs
RUN pip install -e ./shared_libs

# Copy the rag_service code
COPY rag_service/src /app/src

# Copy central config to be accessible in the container
COPY shared_libs/shared_libs/config /app/config

# Set environment variables to use the copied config
ENV CONFIG_PATH=/app/config/config.yaml
ENV DOTENV_PATH=/app/config/.env

# Download the embedding model during the build using fastembed
RUN python -c "import fastembed; fastembed.TextEmbedding(model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# Expose the port that FastAPI will run on
EXPOSE 8000

# Run the API server
CMD ["python", "-m", "uvicorn", "src.handlers.api_handler:app", "--host", "127.0.0.1", "--port", "8000"]
