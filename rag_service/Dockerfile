# Use an official Python runtime as the base image
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY rag_service/requirements.txt .
RUN pip install -r requirements.txt

# Copy shared_libs and install it
COPY shared_libs /app/shared_libs
RUN pip install ./shared_libs

# Copy the rag_service code
COPY rag_service/src /app/src

# Copy central config to be accessible in the container
COPY config /app/config

# Set environment variable to use the copied config
ENV CONFIG_PATH=/app/config/config.yaml
ENV DOTENV_PATH=/app/config/.env

# Run the API server
CMD ["uvicorn", "src.handlers.api_handler:app", "--host", "0.0.0.0", "--port", "8000"]
