import requests
import json
import time

def test_embedding_service(server_url: str, texts, provider: str = "local", is_batch: bool = False):
    """
    Function to test the embedding service at the given server URL.
    
    Args:
        server_url (str): URL of the embedding server's /embed endpoint.
        texts (str or list): Single multi-line text, a single string, or a list of strings.
        provider (str): The embedding provider to use. Default is "local".
        is_batch (bool): Whether to use batch embedding or not. Default is False.
    
    Returns:
        None
    """
    if isinstance(texts, str):
        # If the input is a multi-line string and is_batch is False, send as a single item list
        texts = [texts]

    payload = {
        "texts": texts,
        "provider": provider,
        "is_batch": is_batch
    }

    try:
        start_time = time.time()
        response = requests.post(server_url, json=payload)
        response.raise_for_status()  # Raise an error if the response is not successful
        end_time = time.time()
        request_time = end_time - start_time

        response_data = response.json()
        if "embeddings" in response_data and isinstance(response_data["embeddings"], list):
            print("Embeddings returned in correct form.")
        else:
            print("Embeddings not returned in correct form.")

        print(f"API Request Time: {request_time:.2f} seconds")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while trying to connect to the server: {e}")

if __name__ == "__main__":
    # URL to the embedding server's /embed endpoint
    SERVER_URL = "http://54.91.154.88:8000/embed"

    # Single-line text input
    single_text = "Hello world."
    print("\nTesting Single-line Text:")
    test_embedding_service(SERVER_URL, single_text)

    # Multi-line text input
    multi_line_text = "Hello world.\nThis is a multi-line text example.\nTesting embeddings with FastAPI."
    print("\nTesting Multi-line Text:")
    test_embedding_service(SERVER_URL, multi_line_text, is_batch=False)

    # Batch input (list of strings)
    batch_texts = [
        "Hello world.",
        "FastAPI is awesome!",
        "Multi-line text can also be embedded.",
        "Testing batch embeddings."
    ]
    print("\nTesting Batch Embedding:")
    test_embedding_service(SERVER_URL, batch_texts, is_batch=True)
