from abc import ABC, abstractmethod
from typing import List

class BaseEmbedder(ABC):
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Generate an embedding for the given text.

        :param text: Input text string.
        :return: A list of floats representing the embedding.
        """
        pass

    @abstractmethod
    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.

        :param texts: List of input text strings.
        :return: A list of lists of floats representing embeddings.
        """
        pass

    @abstractmethod
    def vector_size(self) -> int:
        """
        Get the size of the embedding vector.

        :return: Size of the embedding vector.
        """
        pass
