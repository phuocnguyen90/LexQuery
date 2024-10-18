# src/services/get_embedding_function.py

from rag_service.src.services.fe_embed import fe_embed_text 

class FastEmbedWrapper:
    """
    A wrapper class for the custom fast_embed function to mimic BedrockEmbeddings interface.
    """
    def embed(self, text: str) -> list:
        """
        Generate an embedding for the given text.

        :param text: The input text string.
        :return: A list of floats representing the embedding.
        """
        return fe_embed_text(text)

def get_embedding_function():
    """
    Returns an instance of the FastEmbedWrapper.

    :return: An instance with an 'embed' method.
    """
    return FastEmbedWrapper()
