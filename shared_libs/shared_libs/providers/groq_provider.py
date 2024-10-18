# src/providers/groq_provider.py

import logging
from typing import Optional, List, Dict, Any
from groq import Groq 
from .api_provider import APIProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GroqProvider(APIProvider):
    """
    A modular provider for interacting with the Groq LLM API.
    """

    def __init__(self, config: Dict[str, Any], requirements: str):
        """
        Initialize the GroqProvider with the specified configuration.

        :param config: Configuration dictionary containing API keys and settings.
        :param requirements: Preprocessing requirements as a string.
        """
        super().__init__(config, requirements)
        try:
            api_key = config.get('api_key')
            if not api_key:
                logger.error("Groq API key is missing.")
                raise ValueError("Groq API key is missing.")
            self.client = Groq(api_key=api_key)
            self.model_name = config.get('model_name', "llama-3.1-8b-instant")
            self.embedding_model_name = config.get('embedding_model_name', "groq-embedding-001")
            self.temperature = config.get('temperature', 0.7)
            self.max_output_tokens = config.get('max_output_tokens', 4096)
            logger.info("GroqProvider initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize GroqProvider: {e}")
            raise

    def send_single_message(self, prompt: str, stop_sequence: Optional[List[str]] = None) -> Optional[str]:
        """
        Send a single prompt to the Groq API and retrieve the response.

        :param prompt: The prompt to send to Groq.
        :param stop_sequence: Optional list of stop sequences to terminate the LLM response.
        :return: The response content from Groq or None if the call fails.
        """
        try:
            logger.debug("Sending single prompt to Groq API.")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_output_tokens,
                stop=stop_sequence
            )
            logger.debug("Received response from Groq API.")

            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.error("Invalid or empty response structure from Groq API.")
                return None

            content = response.choices[0].message.content.strip()
            if not content:
                logger.error("Empty content received in the response from Groq API.")
                return None

            logger.debug(f"Content received: {content}")

            return content

        except Exception as e:
            logger.error(f"Error during Groq API call: {e}")
            return None

    def send_multi_turn_message(self, conversation_history: List[Dict[str, str]], prompt: str, stop_sequence: Optional[List[str]] = None) -> Optional[str]:
        """
        Send a multi-turn conversation to the Groq API, including conversation history.

        :param conversation_history: List of previous messages (each with a "role" and "content").
                                     The "role" is either "user" or "assistant".
        :param prompt: The current prompt or user input to send to Groq. This will be appended to the conversation history.
        :param stop_sequence: Optional list of stop sequences to terminate the LLM response.
        :return: The response content from Groq or None if the call fails.
        """
        try:
            # Append the current prompt to the conversation history
            conversation_history.append({"role": "user", "content": prompt})

            logger.debug(f"Sending the following conversation history to Groq API: {conversation_history}")

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=conversation_history,
                temperature=self.temperature,
                max_tokens=self.max_output_tokens,
                stop=stop_sequence
            )

            logger.debug("Received response from Groq API.")

            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.error("Invalid or empty response structure from Groq API.")
                return None

            content = response.choices[0].message.content.strip()
            if not content:
                logger.error("Empty content received in the response from Groq API.")
                return None

            # Append the assistant's response to the conversation history
            conversation_history.append({"role": "assistant", "content": content})

            logger.debug(f"Content received: {content}")

            return content

        except Exception as e:
            logger.error(f"Error during Groq API call: {e}")
            return None

    def create_embedding(self, text: str) -> Optional[List[float]]:
        """
        Create an embedding for the given text using the Groq embedding model.

        :param text: The input text to create an embedding for.
        :return: A list representing the embedding vector or None if the call fails.
        """
        try:
            logger.debug("Sending request to Groq API for embedding.")
            response = self.client.embeddings.create(
                model=self.embedding_model_name,
                input=text
            )
            logger.debug("Received response from Groq API for embedding.")

            if not response or 'data' not in response or len(response['data']) == 0:
                logger.error("Invalid or empty response structure from Groq embedding API.")
                return None

            embedding = response['data'][0]['embedding']
            logger.debug(f"Embedding received: {embedding}")

            return embedding

        except Exception as e:
            logger.error(f"Error during Groq API embedding call: {e}")
            return None