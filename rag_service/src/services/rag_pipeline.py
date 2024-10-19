import os
from typing import Dict
from shared_libs.config.config_loader import ConfigLoader
from shared_libs.providers import GroqProvider, OpenAIProvider

# Load configuration
config = ConfigLoader.load_config(config_path='config/config.yaml', dotenv_path='config/.env')

# Access environment variables from the .env file
llm_api_key = os.getenv("LLM_API_KEY")

# Access specific LLM settings from the YAML config
provider_name = config.get("provider", "groq")
llm_settings = config.get(provider_name, {})

# Initialize the appropriate LLM provider
if provider_name == "groq":
    provider = GroqProvider(config=llm_settings, requirements="some_requirements")
elif provider_name == "openai":
    provider = OpenAIProvider(config=llm_settings, requirements="some_requirements")

from shared_libs.providers import APIProvider
from shared_libs.prompts.default_prompts import SYSTEM_PROMPT
from search_qdrant import search_qdrant

class RAGPipeline:
    def __init__(self, provider: APIProvider):
        self.provider = provider

    def process(self, query_text: str) -> Dict:
        # Step 1: Retrieve relevant documents from Qdrant
        retrieved_docs = search_qdrant(query_text, top_k=3)
        if not retrieved_docs:
            return {
                "query_text": query_text,
                "response_text": "No relevant documents found.",
                "sources": []
            }

        # Step 2: Construct the context and prompt for LLM
        context = "\n\n---\n\n".join([f"Document ID: {doc['record_id']}\nContent: {doc['content']}" for doc in retrieved_docs])
        full_prompt = SYSTEM_PROMPT.format(query=query_text, context=context)

        # Step 3: Generate response using LLM
        response_text = self.provider.send_single_message(full_prompt)
        if not response_text:
            response_text = "An error occurred while generating the response."

        # Step 4: Return the generated response along with the sources
        return {
            "query_text": query_text,
            "response_text": response_text,
            "sources": [doc['record_id'] for doc in retrieved_docs]
        }
