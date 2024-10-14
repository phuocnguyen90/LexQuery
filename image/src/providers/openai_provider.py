# providers/openai_provider.py

import logging
import openai  # Make sure the OpenAI library is installed
from providers.api_provider import APIProvider
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIProvider(APIProvider):
    """
    A modular provider for interacting with the OpenAI API.
    """

    def __init__(self, config: Dict[str, Any], requirements: str):
        """
        Initialize the OpenAIProvider with the specified configuration.

        :param config: Configuration dictionary containing API keys and settings.
        :param requirements: Preprocessing requirements as a string.
        """
        super().__init__(config, requirements)  # Pass both config and requirements to the parent
        try:
            api_key = config.get("api_key")
            if not api_key:
                logger.error("OpenAI API key is missing.")
                raise ValueError("OpenAI API key is missing.")
            openai.api_key = api_key  # Set the OpenAI API key
            
            self.model_name = config.get("model_name", "gpt-3.5-turbo")  # Default to GPT-3.5 Turbo
            self.temperature = config.get("temperature", 0.7)
            self.max_output_tokens = config.get("max_output_tokens", 150)  # Adjust max tokens as needed
            
            logger.info("OpenAIProvider initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAIProvider: {e}")
            raise

    def send_message(self, prompt: str, stop_sequence: Optional[List[str]] = None) -> Optional[str]:
        """
        Send a message to the OpenAI API and retrieve the response.

        :param prompt: The prompt to send to OpenAI.
        :param stop_sequence: Optional list of stop sequences to terminate the LLM response.
        :return: The response content from OpenAI or None if the call fails.
        """
        try:
            logger.debug("Sending prompt to OpenAI API.")
            
            response = openai.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_output_tokens,
                stop=stop_sequence
            )
            logger.debug("Received response from OpenAI API.")

            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.error("Invalid or empty response structure from OpenAI API.")
                return None

            content = response.choices[0].message.content.strip()
            if not content:
                logger.error("Empty content received in the response from OpenAI API.")
                return None
            
            logger.debug(f"Content received: {content}")
            return content
            
        except Exception as e:
            logger.error(f"Error during OpenAI API call: {e}")
            return None
