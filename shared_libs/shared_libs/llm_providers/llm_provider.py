# src/providers/llm_provider.py

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

class LLMProvider(ABC):
    """
    Abstract base class for API providers.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the API provider with configuration and processing requirements.
        
        :param config: Configuration dictionary containing API keys and settings.
        :param requirements: Preprocessing requirements as a string.
        """
        self.config = config
        

    @abstractmethod
    async def send_single_message(self, prompt: str, stop_sequence: Optional[List[str]] = None) -> Optional[str]:
        """
        Asynchronously send a message to the LLM API and retrieve the response.
        Must be implemented by subclasses.
        
        :param prompt: The prompt to send to the LLM.
        :param stop_sequence: Optional list of stop sequences to terminate the LLM response.
        :return: The response content from the LLM or None if the call fails.
        """
        pass

    async def send_multi_turn_message(self, conversation_history: List[Dict[str, str]], prompt: str, stop_sequence: Optional[List[str]] = None) -> Optional[str]:
        """
        Asynchronously send a multi-turn conversation to the LLM API, including conversation history.
        Must be implemented by subclasses.
        
        :param conversation_history: List of previous messages.
        :param prompt: The prompt to send to the LLM.
        :param stop_sequence: Optional list of stop sequences to terminate the LLM response.
        :return: The response content from the LLM or None if the call fails.
        """
        pass
