# providers/ollama_provider.py

import logging
import requests  # Make sure the requests library is installed
from .llm_provider import LLMProvider
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    """
    A modular provider for interacting with the Ollama API.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the OllamaProvider with the specified configuration.

        :param config: Configuration dictionary containing API keys and settings.
        :param requirements: Preprocessing requirements as a string.
        """
        super().__init__() 
        try:
            self.base_url = config.get("ollama_api_url", "http://localhost:11434")  # Default to local Ollama instance
            self.model_name = config.get('model_name', "llama3.1")
            logger.info("OllamaProvider initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize OllamaProvider: {e}")
            raise

    def send_single_message(self, prompt: str, stop_sequence: Optional[List[str]] = None) -> Optional[str]:
        """
        Send a message to the Ollama API and retrieve the response.

        :param prompt: The prompt to send to Ollama.
        :param stop_sequence: Optional list of stop sequences to terminate the LLM response.
        :return: The response content from Ollama or None if the call fails.
        """
        try:
            logger.debug("Sending prompt to Ollama API.")
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }

            response = requests.post(f"{self.base_url}/api/generate", json=payload)



            # Check for response status
            if response.status_code != 200:
                logger.error(f"Failed to get a valid response from Ollama API: {response.status_code} {response.text}")
                return None

            result = response.json()

            # Check if the response contains the expected data
            if "text" not in result:
                logger.error("Invalid response structure from Ollama API.")
                return None

            content = result["text"].strip()
            if not content:
                logger.error("Empty content received in the response from Ollama API.")
                return None

            logger.debug(f"Content received: {content}")
            return content
            
        except Exception as e:
            logger.error(f"Error during Ollama API call: {e}")
            return None
