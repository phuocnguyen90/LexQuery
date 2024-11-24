from typing import List, Dict
from shared_libs.llm_providers import ProviderFactory
from shared_libs.utils.logger import Logger
from shared_libs.config.config_loader import AppConfigLoader

config=AppConfigLoader()
llm_provider_name=config.get('llm', {}).get('provider', 'groq')

logger = Logger.get_logger(module_name=__name__)

class IntentionDetector:
    def __init__(self, provider=None, max_retries=2):
        """
        Initializes the IntentionDetector with an LLM provider and a retry limit.
        :param provider: LLM provider instance. Defaults to the globally configured LLM provider.
        :param max_retries: Maximum number of retries if the LLM response is not in the expected format.
        """
        llm_settings = config.get('llm', {}).get(llm_provider_name, {})

        self.provider = provider or ProviderFactory.get_provider(name=llm_provider_name, config=llm_settings)
        self.max_retries = max_retries

    async def detect_intention(self, query_text: str, conversation_history: List[Dict[str, str]]) -> str:
        """
        Uses an LLM to classify the intention of the query with retry logic.
        Expected responses: ['irrelevant', 'history', 'rag'].

        :param query_text: The user's query.
        :param conversation_history: List of conversation messages.
        :return: One of ['irrelevant', 'history', 'rag'].
        """
        retries = 0
        while retries < self.max_retries:
            try:
                # Construct the classification prompt
                history_text = "\n".join([f"User: {msg['text']}" for msg in conversation_history])
                prompt = f"""
You are an assistant that classifies user queries into one of the following categories:
1. 'irrelevant': The query is not related to the task or context.
2. 'history': The query can be answered based on the provided conversation history.
3. 'rag': External information from a database is required to answer the query.

Conversation History:
{history_text or "No prior conversation."}

User Query:
"{query_text}"

Your response should be one of the following: 'irrelevant', 'history', or 'rag'.
"""

                # Call the LLM with the classification prompt
                response = await self.provider.send_single_message(prompt=prompt)
                logger.debug(f"LLM response for intention detection: {response}")

                # Parse and validate the response
                classification = response.strip().lower()
                if classification in ['irrelevant', 'history', 'rag']:
                    return classification

                # Log unrecognized response and retry
                logger.warning(f"Unrecognized LLM classification: {classification}. Retrying...")

            except Exception as e:
                logger.error(f"Error during intention detection: {str(e)}. Retrying...")

            retries += 1

        # If all retries fail, default to 'rag'
        logger.error(f"Intention detection failed after {self.max_retries} retries. Defaulting to 'rag'.")
        return 'rag'
