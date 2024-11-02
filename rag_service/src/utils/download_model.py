# download_model.py

import os
import fastembed

def main():
    # Define the model you want to download
    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


    try:
        # Instantiate TextEmbedding to download the model
        embedder = fastembed.TextEmbedding(model_name=model_name)
        # Optionally, you can perform a dummy embed to ensure the model is loaded
        # For example:
        _ = embedder.embed("Test")
        
    except Exception as e:
        print(f"Failed to download the model '{model_name}': {e}")
        exit(1)

if __name__ == "__main__":
    main()
