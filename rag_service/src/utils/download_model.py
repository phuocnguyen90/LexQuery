# download_model.py

import os
import fastembed

def main():
    # Define the model you want to download
    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # Define the cache directory where the model will be stored
    cache_dir = "/app/models"

    # Ensure the cache directory exists
    os.makedirs(cache_dir, exist_ok=True)

    try:
        # Instantiate TextEmbedding to download the model
        embedder = fastembed.TextEmbedding(model_name=model_name, cache_dir=cache_dir)
        # Optionally, you can perform a dummy embed to ensure the model is loaded
        # For example:
        # _ = embedder.embed("Test")
        print(f"Model '{model_name}' downloaded successfully to '{cache_dir}'")
    except Exception as e:
        print(f"Failed to download the model '{model_name}': {e}")
        exit(1)

if __name__ == "__main__":
    main()
