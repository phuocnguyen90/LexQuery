from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
import sys

def reset_collection(collection_name: str):
    """
    Deletes all data in the specified Qdrant collection after user confirmation.

    :param collection_name: Name of the Qdrant collection to reset.
    """
    try:
        # Connect to the Qdrant instance running on Docker (localhost:6333)
        client = QdrantClient(url="http://localhost:6333")

        # Check if the collection exists
        try:
            client.get_collection(collection_name)
            print(f"Collection '{collection_name}' exists. Proceeding with confirmation.")
        except UnexpectedResponse:
            print(f"Collection '{collection_name}' does not exist. Nothing to reset.")
            return

        # Confirm deletion
        confirmation = input(f"Are you sure you want to delete the collection '{collection_name}'? (yes/no): ").strip().lower()
        if confirmation != 'yes':
            print("Operation cancelled.")
            return

        # Delete the collection
        client.delete_collection(collection_name)
        print(f"Collection '{collection_name}' deleted successfully.")

        # Optionally recreate the collection (if needed)
        recreate = input(f"Do you want to recreate the collection '{collection_name}'? (yes/no): ").strip().lower()
        if recreate == 'yes':
            vector_size = 384  # Example vector size; update based on your model
            client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "size": vector_size,
                    "distance": "Cosine"  # Update distance metric if necessary
                }
            )
            print(f"Collection '{collection_name}' recreated successfully.")
        else:
            print("Collection was not recreated.")
    except Exception as e:
        print(f"Error resetting collection '{collection_name}': {e}")
        sys.exit(1)

# Example usage
if __name__ == "__main__":
    collection_name = "legal_doc"  # Replace with your collection name
    reset_collection(collection_name)
