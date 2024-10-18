# providers/gemini_provider.py

import logging
import google.generativeai as genai
from .api_provider import APIProvider
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiProvider(APIProvider):
    """
    A modular provider for interacting with the Google Gemini API.
    """

    def __init__(self, config: Dict[str, Any], requirements: str):
        super().__init__(config, requirements)  # Pass both config and requirements to the parent
        try:
            api_key = config.get("api_key")
            if not api_key:
                logger.error("Google Gemini API key is missing.")
                raise ValueError("Google Gemini API key is missing.")

            self.api_key = api_key
            self.model_name = config.get("model_name", "gemini-1.5-flash")

            self.generation_config = genai.configure(api_key=self.api_key)

            # Set up the generation configuration
            self.generation_config = genai.GenerationConfig(
                temperature=config.get("temperature", 0.0),
                top_p=config.get("top_p", 0.8),
                top_k=config.get("top_k", 32),
                candidate_count=config.get("candidate_count", 1),
                max_output_tokens=config.get("max_output_tokens", 2048),
            )
            
            logger.info("GoogleGeminiProvider initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize GoogleGeminiProvider: {e}")
            raise

    def send_single_message(self, prompt: str) -> Optional[str]:
        """
        Send a single prompt to the Google Gemini API and retrieve the response.
        """
        try:
            logger.debug("Sending single prompt to Google Gemini API.")
            model = genai.GenerativeModel(self.model_name)

            response = model.generate_content(
                contents=prompt,
                generation_config=self.generation_config,
                stream=False,
                tools=[],
            )

            logger.debug("Received response from Google Gemini API.")
            if not response or not response.candidates:
                logger.error("Invalid or empty response structure from Google Gemini API.")
                return None

            generated_text = response.candidates[0].content.parts[0].text.strip()
            if not generated_text:
                logger.error("Empty content received in the response from Google Gemini API.")
                return None

            logger.debug(f"Content received: {generated_text}")
            return generated_text

        except Exception as e:
            logger.error(f"Error during Google Gemini API call: {e}")
            return None

    def send_multi_turn_message(self, conversation_history: List[Dict[str, str]], prompt: str) -> Optional[str]:
        """
        Send a multi-turn conversation to the Google Gemini API, including conversation history.
        """
        try:
            # Create the complete prompt by concatenating conversation history with the new prompt
            full_conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
            full_prompt = f"{full_conversation}\nuser: {prompt}"

            logger.debug(f"Sending multi-turn conversation to Google Gemini API.")
            return self.send_single_message(full_prompt)

        except Exception as e:
            logger.error(f"Error during multi-turn message to Google Gemini API: {e}")
            return None
