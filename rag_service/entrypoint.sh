#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Function to load environment variables from .env
load_env() {
    if [ -f /app/config/.env ]; then
        echo "Loading environment variables from /app/config/.env"
        # Export all variables from .env, handling spaces and special characters
        set -a
        source /app/config/.env
        set +a
    else
        echo "WARNING: /app/config/.env file not found. Proceeding without it."
    fi
}

# Load environment variables
load_env

# Verify AWS_REGION is correctly loaded
if [ -z "$AWS_REGION" ]; then
    echo "ERROR: AWS_REGION is not set"
    exit 1
fi

# Trim whitespace and newline characters from AWS_REGION
AWS_REGION=$(echo "$AWS_REGION" | tr -d '[:space:]')
export AWS_REGION
echo "Trimmed AWS_REGION='${AWS_REGION}'"

# Download the embedding model if not already available
echo "Downloading the embedding model..."
python -c "import fastembed; fastembed.TextEmbedding(model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2').download_model(model='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='/app/models')"
# Run the API server
echo "Starting the API server..."
exec uvicorn src.handlers.api_handler:app --host 0.0.0.0 --port 8000
