#!/bin/bash

# Load environment variables from .env file
if [ -f /app/config/.env ]; then
    export $(grep -v '^#' /app/config/.env | xargs)
fi

# Verify AWS_REGION is correctly loaded
if [ -z "$AWS_REGION" ]; then
    echo "ERROR: AWS_REGION is not set"
    exit 1
fi


# Download the embedding model if not already available
python -c "import fastembed; fastembed.TextEmbedding(model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2').download_model()"

# Run the API server
exec uvicorn src.handlers.api_handler:app --host 127.0.0.1 --port 8000
