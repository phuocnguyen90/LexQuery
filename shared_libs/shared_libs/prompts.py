import yaml
import os

PROMPT_CONFIG_PATH = os.getenv('PROMPT_CONFIG_PATH', 'shared_libs/prompts/prompts.yaml')

def get_prompt(prompt_name: str) -> str:
    """
    Load a prompt template by name from the YAML configuration file.

    :param prompt_name: The name of the prompt to load.
    :return: The prompt template as a string.
    """
    try:
        with open(PROMPT_CONFIG_PATH, 'r', encoding='utf-8') as file:
            prompts = yaml.safe_load(file)
            if prompt_name in prompts:
                return prompts[prompt_name]
            else:
                raise ValueError(f"Prompt '{prompt_name}' not found in the configuration.")
    except Exception as e:
        raise RuntimeError(f"Failed to load prompt configuration: {str(e)}")
