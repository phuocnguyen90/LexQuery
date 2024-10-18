# providers/openai_provider.py

import logging
import openai  # Make sure the OpenAI library is installed
from llm_providers.api_provider import APIProvider
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIProvider(APIProvider):
    """
    A modular provider for interacting with the OpenAI API.
    """

    def __init__(self, config: Dict[str, Any], requirements: str):
        super().__init__(config, requirements)  # Pass both config and requirements to the parent
        try:
            api_key = config.get("api_key")
            if not api_key:
                logger.error("OpenAI API key is missing.")
                raise ValueError("OpenAI API key is missing.")
            openai.api_key = api_key
            
            self.model_name = config.get("model_name", "gpt-3.5-turbo")
            self.temperature = config.get("temperature", 0.7)
            self.max_output_tokens = config.get("max_output_tokens", 150)

            logger.info("OpenAIProvider initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAIProvider: {e}")
            raise

    def send_single_message(self, prompt: str, stop_sequence: Optional[List[str]] = None) -> Optional[str]:
        """
        Send a single prompt to the OpenAI API and retrieve the response.
        """
        try:
            logger.debug("Sending single prompt to OpenAI API.")
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_output_tokens,
                stop=stop_sequence
            )

            logger.debug("Received response from OpenAI API.")
            if not response or not response.choices:
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

    def send_multi_turn_message(self, conversation_history: List[Dict[str, str]], prompt: str, stop_sequence: Optional[List[str]] = None) -> Optional[str]:
        """
        Send a multi-turn conversation to the OpenAI API, including conversation history.
        """
        try:
            # Append the current user prompt to the conversation history
            conversation_history.append({"role": "user", "content": prompt})

            logger.debug(f"Sending conversation history with new prompt to OpenAI API.")
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=conversation_history,
                temperature=self.temperature,
                max_tokens=self.max_output_tokens,
                stop=stop_sequence
            )

            logger.debug("Received response from OpenAI API.")
            if not response or not response.choices:
                logger.error("Invalid or empty response structure from OpenAI API.")
                return None

            content = response.choices[0].message.content.strip()
            if not content:
                logger.error("Empty content received in the response from OpenAI API.")
                return None

            # Add the assistant's response to the conversation history for future use
            conversation_history.append({"role": "assistant", "content": content})
            
            logger.debug(f"Content received: {content}")
            return content

        except Exception as e:
            logger.error(f"Error during OpenAI API call: {e}")
            return None
