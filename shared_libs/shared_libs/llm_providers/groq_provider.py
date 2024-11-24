# src/providers/groq_provider.py

import logging
import asyncio
from typing import Optional, List, Dict, Any

import httpx
from functools import partial
from .llm_provider import LLMProvider


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GroqProvider(LLMProvider):
    """
    A modular provider for interacting with the Groq LLM API via direct HTTP requests.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the GroqProvider with the specified configuration.

        :param config: Configuration dictionary containing API keys and settings.
        """
        super().__init__(config)
        try:
            self.api_key = config.get('api_key')
            if not self.api_key:
                logger.error("Groq API key is missing.")
                raise ValueError("Groq API key is missing.")
            self.base_url = "https://api.groq.com/openai/v1/chat/completions"
            self.model_name = config.get('model_name', "llama-3.1-8b-instant")
            self.temperature = config.get('temperature', 0.7)
            self.max_output_tokens = config.get('max_output_tokens', 2048)
            logger.info("GroqProvider initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize GroqProvider: {e}")
            raise

    async def send_single_message(self, prompt: Optional[str] = None, message_payload: Optional[Dict[str, Any]] = None) -> str:
        """
        Send a single message to the Groq API and return the response.

        :param prompt: A simple text prompt to send to the model.
        :param message_payload: A dictionary payload for more complex interactions.
        :return: The generated response from the model.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if prompt is not None:
            # Construct messages array with the prompt
            messages = [{"role": "user", "content": prompt}]
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_output_tokens,
            }
        elif message_payload is not None:
            # Use the provided message payload
            payload = {
                "model": self.model_name,
                "temperature": self.temperature,
                "max_tokens": self.max_output_tokens,
                **message_payload  # Merge additional payload
            }
        else:
            raise ValueError("Either 'prompt' or 'message_payload' must be provided to send a message.")
        # logger.debug(f"Payload being sent to Groq API: {json.dumps(payload, indent=2)}")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=60  # Adjust timeout as needed
                )
                response.raise_for_status()
                data = response.json()
                if 'error' in data:
                    error = data['error']
                    logger.error(f"Groq API Error [{error.get('code')}]: {error.get('message')}")
                    raise ValueError(f"Groq API Error [{error.get('code')}]: {error.get('message')}")
                # Extract the assistant's reply
                assistant_reply = data['choices'][0]['message']['content']
                return assistant_reply.strip()
            except httpx.HTTPError as http_err:
                logger.error(f"HTTP error occurred: {http_err}")
                raise
            except Exception as e:
                logger.error(f"Error during Groq API call: {e}")
                raise


    async def send_multi_turn_message(
        self,
        conversation_history: List[Dict[str, str]],
        prompt: str,
        stop_sequence: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Asynchronously send a multi-turn conversation to the Groq API, including conversation history.

        :param conversation_history: List of previous messages.
        :param prompt: The current prompt or user input to send to Groq.
        :param stop_sequence: Optional list of stop sequences to terminate the LLM response.
        :return: The response content from Groq or None if the call fails.
        """
        try:
            # Append the current prompt to the conversation history
            conversation_history.append({"role": "user", "content": prompt})

            logger.debug(f"Sending the following conversation history to Groq API: {conversation_history}")

            # Construct the message payload
            message_payload = {
                "messages": conversation_history
            }

            if stop_sequence:
                message_payload["stop"] = stop_sequence

            # Log the payload being sent (excluding sensitive information)
            logger.debug(f"Message payload being sent to Groq API: {json.dumps(message_payload, indent=2)}")

            # Send the message_payload using the send_single_message method
            response = await self.send_single_message(message_payload=message_payload)

            logger.debug("Received response from Groq API.")

            if not response:
                logger.error("Invalid or empty response from Groq API.")
                return None

            # Append the assistant's response to the conversation history
            conversation_history.append({"role": "assistant", "content": response})

            logger.debug(f"Content received: {response}")

            return response

        except Exception as e:
            logger.error(f"Error during Groq API call: {e}")
            return None
