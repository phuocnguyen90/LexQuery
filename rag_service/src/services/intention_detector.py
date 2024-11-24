from typing import List, Dict, Tuple
import json
from shared_libs.llm_providers import ProviderFactory
from shared_libs.utils.logger import Logger
from shared_libs.config.config_loader import AppConfigLoader
import re

config=AppConfigLoader()
llm_provider_name=config.get('llm', {}).get('provider', 'groq')
llm_config = config.get('llm', {}).get(llm_provider_name, {})

logger = Logger.get_logger(module_name=__name__)



class IntentionDetector:
    def __init__(self, provider=None, max_retries=3):
        # Load configurations
        config = AppConfigLoader()
        groq_config = config.get('llm', {}).get('groq', {})
        
        # Retrieve the API key
        api_key = groq_config.get('api_key')
        # Hardcode the larger model name and temperature
        
        model_name = "llama3-70b-8192"  
        temperature = 0.1  # For deterministic output

        # Create a dedicated configuration for the intention detector
        intention_detector_llm_config = {
            'api_key': api_key,
            'model_name': model_name,
            'temperature': temperature,
            'max_output_tokens': 512  
        }

        # Initialize the LLM provider with the specific configuration
        self.provider = ProviderFactory.get_provider('groq', intention_detector_llm_config)
        self.max_retries = max_retries


    async def detect_intention(
        self, query_text: str, conversation_history: List[Dict[str, str]]
    ) -> Tuple[str, str]:
        """
        Uses an LLM to classify the intention of the query and generate response_text.
        
        :param query_text: The user's query.
        :param conversation_history: List of conversation messages.
        :return: A tuple (intention, response_text).
        """
        retries = 0
        while retries < self.max_retries:
            try:
                # Construct the classification and response prompt
                refuse_answer="""Xin lỗi nhưng tôi không thể trả lời câu hỏi này"""
                history_text = "\n".join([f"User: {msg['text']}" for msg in conversation_history])
                prompt = f"""
                    You are an assistant that classifies user queries and generates responses in JSON format.
                    Possible classifications:
                    1. 'irrelevant': The query is unrelated to legal matters.
                    2. 'history': The query can be answered based on the provided conversation history.
                    3. 'rag': External information from a database is required to answer the query.

                    Conversation History:
                    {history_text or "No prior conversation."}

                    User Query:
                    "{query_text}"

                    Your response must be in JSON format:
                    - For irrelevant: {{ "irrelevant": {refuse_answer} }}
                    - For history: {{ "history": "<response_text>" }}
                    - For rag: {{ "rag": null }}
                    """

                # Call the LLM with the prompt
                response = await self.provider.send_single_message(prompt=prompt)
                logger.debug(f"LLM response for intention detection: {response}")

                # Validate and parse JSON response
                parsed_response = self._validate_and_parse_json(response)
                if parsed_response:
                    # Check which key exists in the JSON response
                    if "irrelevant" in parsed_response:
                        return "irrelevant", parsed_response["irrelevant"]
                    elif "history" in parsed_response:
                        return "history", parsed_response["history"]
                    elif "rag" in parsed_response:
                        return "rag", None

                # Log unrecognized response and retry
                logger.warning(f"Invalid or unrecognized LLM response: {response}. Retrying...")

            except Exception as e:
                logger.error(f"Error during intention detection: {str(e)}. Retrying...")

            retries += 1

        # Default to 'rag' if retries are exhausted
        logger.error(f"Intention detection failed after {self.max_retries} retries. Defaulting to 'rag'.")
        return "rag", None

    def _validate_and_parse_json(self, response: str) -> Dict:
        """
        Extracts JSON object from the LLM response.
        """
        try:
            # Use regex to find JSON object in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed_response = json.loads(json_str)
                if isinstance(parsed_response, dict):
                    return parsed_response
        except json.JSONDecodeError:
            logger.warning(f"Response is not valid JSON: {response}")
        return None
