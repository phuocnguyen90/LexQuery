# utils/llm_formatter.py

import logging
import json
import yaml
from typing import Optional, Dict, Any
from providers import ProviderFactory  
from providers.openai_provider import OpenAIProvider
from providers.groq_provider import GroqProvider
from providers.api_provider import APIProvider
from utils.validation import detect_text_type, is_english
# from utils.record import Record
# logging.getLogger(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMFormatter:
    """
    Unified LLM Formatter supporting multiple formatting and enrichment modes and providers.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LLMFormatter, cls).__new__(cls)
        return cls._instance

    def __init__(self, config: Dict[str, Any], prompts_path: str = "src/config/schemas/prompts.yaml"):
        if not hasattr(self, 'initialized'):  # Avoid re-initializing
            self.config = config
            self.prompts = self._load_prompts(prompts_path)
            self.provider_name = self.config.get('provider', 'openai').lower()
            self.provider = self._initialize_provider()
            self.initialized = True  # Mark as initialized
            logger.info(f"LLMFormatter initialized with provider '{self.provider_name}'.")

    def _load_prompts(self, prompts_path: str) -> Dict[str, Any]:
        """
        Load prompts from the specified YAML file.

        :param prompts_path: Path to the YAML file containing prompts.
        :return: Dictionary of prompts.
        """
        try:
            with open(prompts_path, 'r', encoding='utf-8') as file:
                prompts = yaml.safe_load(file)
            logger.info(f"Loaded prompts from '{prompts_path}'.")
            return prompts.get('prompts', {})
        except FileNotFoundError:
            logger.error(f"Prompts file '{prompts_path}' not found.")
            raise
        except yaml.YAMLError as ye:
            logger.error(f"YAML parsing error in '{prompts_path}': {ye}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading prompts '{prompts_path}': {e}")
            raise

    def _initialize_provider(self) -> APIProvider:
        """
        Initialize the API provider based on the configuration.

        :return: An instance of the API provider.
        """
        provider_name = self.provider_name
        if not provider_name:
            logger.error("API provider not specified in the configuration.")
            raise ValueError("API provider not specified in the configuration.")

        provider_config = self.config.get(provider_name, {})
        if not provider_config:
            logger.error(f"No configuration found for provider '{provider_name}'.")
            raise ValueError(f"No configuration found for provider '{provider_name}'.")

        # Retrieve requirements if any (used by some providers)
        requirements = self.config.get('processing', {}).get('pre_process_requirements', "")
        try:
            provider = ProviderFactory.get_provider(provider_name, provider_config, requirements)
            logger.info(f"Initialized provider: {provider_name}")
            return provider
        except Exception as e:
            logger.error(f"Failed to initialize provider '{provider_name}': {e}")
            raise

    def format_text(
        self, 
        raw_text: str, 
        mode: str = "tagged", 
        record_type: Optional[str] = None, 
        json_schema: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Format raw text into structured formats using the specified mode and provider.

        :param raw_text: The raw text input (could be tagged, json, or unformatted).
        :param mode: The desired formatting mode ("tagged", "json", or "enrichment").
        :param record_type: Type of the record ("QA" or "DOC") for enrichment mode.
        :param json_schema: JSON schema for "json" mode.
        :return: Formatted text as per the specified mode or None if formatting fails.
        """
        try:
            # Detect the input text type
            text_type = detect_text_type(raw_text)
            logger.debug(f"Detected text type: {text_type}")

            # If input is unformatted, convert it to tagged using LLMFormatter
            if text_type == "unformatted":
                if mode != "tagged":
                    logger.error("Unformatted input can only be converted to 'tagged' mode.")
                    return None
                logger.info("Converting unformatted text to tagged format using LLMFormatter.")
                # Retrieve the tagged prompt template
                prompt_template = self.prompts.get('formatting', {}).get('tagged', {}).get('prompt')
                if not prompt_template:
                    logger.error("Tagged prompt template not found in prompts.yaml.")
                    return None
                # Format the prompt with the raw_text
                prompt = prompt_template.format(raw_text=raw_text)
                # Send the prompt to the provider
                formatted_output = self.provider.send_single_message(prompt=prompt)
                if not formatted_output:
                    logger.error("LLMFormatter failed to convert unformatted text to tagged format.")
                    return None
                raw_text = formatted_output  # Update raw_text to tagged format
                text_type = "tagged"  # Update text_type after conversion
                logger.debug("Successfully converted unformatted text to tagged format.")

            # Handle based on desired mode
            if mode == "tagged":
                if text_type == "tagged":
                    logger.info("Input is already in tagged format. Returning as-is.")
                    return raw_text
                elif text_type == "json":
                    logger.info("Converting JSON to tagged format.")
                    prompt_template = self.prompts.get('formatting', {}).get('tagged', {}).get('prompt')
                    if not prompt_template:
                        logger.error("Tagged prompt template not found in prompts.yaml.")
                        return None
                    prompt = prompt_template.format(raw_text=raw_text)
                    formatted_output = self.provider.send_single_message(prompt=prompt)
                    if not formatted_output:
                        logger.error("LLMFormatter failed to convert JSON to tagged format.")
                        return None
                    return formatted_output

            elif mode == "json":
                if text_type == "json":
                    logger.info("Input is already in JSON format. Returning as-is.")
                    return raw_text
                elif text_type == "tagged":
                    logger.info("Converting tagged format to JSON.")
                    prompt_template = self.prompts.get('formatting', {}).get('json', {}).get('prompt')
                    if not prompt_template:
                        logger.error("JSON prompt template not found in prompts.yaml.")
                        return None
                    if not json_schema:
                        logger.error("json_schema must be provided for json formatting mode.")
                        return None
                    json_schema_str = json.dumps(json_schema, indent=2)
                    prompt = prompt_template.format(raw_text=raw_text, json_schema=json_schema_str)
                    formatted_output = self.provider.send_single_message(prompt=prompt)
                    if not formatted_output:
                        logger.error("LLMFormatter failed to convert tagged format to JSON.")
                        return None
                    return formatted_output

            elif mode == "enrichment":
                logger.info("Performing enrichment on the input text.")
                prompt_template = self.prompts.get('enrichment', {}).get('enrichment_prompt')
                if not prompt_template:
                    logger.error("Enrichment prompt template not found in prompts.yaml.")
                    return None
                if not record_type:
                    logger.error("record_type must be specified for enrichment mode.")
                    return None
                prompt = prompt_template.format(chunk_text=raw_text)
                formatted_output = self.provider.send_single_message(prompt=prompt)
                if not formatted_output:
                    logger.error("LLMFormatter failed to perform enrichment.")
                    return None
                return formatted_output

            else:
                logger.error(f"Unsupported formatting mode: {mode}")
                return None

        except Exception as e:
            logger.error(f"Error in format_text method: {e}")
            return None

    
    def _initialize_provider_override(self, provider: str) -> APIProvider:
        """
        Initialize a different provider on the fly.

        :param provider: The LLM provider to use ("openai", "groq", etc.).
        :return: An instance of the specified API provider.
        """
        provider = provider.lower()
        provider_config = self.config.get(provider, {})
        if not provider_config:
            logger.error(f"No configuration found for provider '{provider}'.")
            raise ValueError(f"No configuration found for provider '{provider}'.")

        # Retrieve requirements if any (used by some providers)
        requirements = self.config.get('processing', {}).get('pre_process_requirements', "")
        try:
            provider_instance = ProviderFactory.get_provider(provider, provider_config, requirements)
            logger.info(f"Initialized provider: {provider}")
            return provider_instance
        except Exception as e:
            logger.error(f"Failed to initialize provider '{provider}': {e}")
            raise

    def translate(self, record) -> None:
        """ 
        Translate the title and content of the record to Vietnamese if they are in English.
        Uses the LLM to perform the translation and updates the record object directly.
        """
        try:
            # Translate title if it is in English
            if is_english(record.title):
                logger.info(f"Translating title for record ID {record.record_id} to Vietnamese.")
                title_prompt = f"Translate the following English text to Vietnamese: '{record.title}'"
                translated_title = self.provider.send_single_message(title_prompt)
                if translated_title:
                    record.title = translated_title.strip()  # Update title with translated text
                else:
                    logger.warning(f"Translation for title of record ID {record.record_id} failed or returned empty.")

            # Translate content if it is in English
            if is_english(record.content):
                logger.info(f"Translating content for record ID {record.record_id} to Vietnamese.")
                content_prompt = f"Translate the following English text to Vietnamese: '{record.content}'"
                translated_content = self.provider.send_single_message(content_prompt)
                if translated_content:
                    record.content = translated_content.strip()  # Update content with translated text
                else:
                    logger.warning(f"Translation for content of record ID {record.record_id} failed or returned empty.")

            logger.info(f"Translation completed for record ID {record.record_id}.")
        except Exception as e:
            logger.error(f"Error during translation for record ID {record.record_id}: {e}")

