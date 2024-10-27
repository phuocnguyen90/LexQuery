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
