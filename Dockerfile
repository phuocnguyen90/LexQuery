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

# Convert .env to Unix line endings
RUN sed -i 's/\r$//' /app/config/.env

# Copy entrypoint script
COPY rag_service/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set environment variables for configuration paths
ENV CONFIG_PATH=/app/config/config.yaml
ENV DOTENV_PATH=/app/config/.env
# RUN export $(grep -v '^#' /app/.env | xargs)

# Expose the port that FastAPI will run on
EXPOSE 8000

# Run the entrypoint script which loads env variables and runs the server
ENTRYPOINT ["/app/entrypoint.sh"]