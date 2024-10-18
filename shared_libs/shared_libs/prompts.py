#shared_libs/prompts.py
import yaml
import os
from pathlib import Path

# Set a default path for prompts.yaml if PROMPT_CONFIG_PATH environment variable is not provided
DEFAULT_PROMPT_CONFIG_PATH = Path(__file__).resolve().parent / "prompts" / "prompts.yaml"
PROMPT_CONFIG_PATH = os.getenv('PROMPT_CONFIG_PATH', str(DEFAULT_PROMPT_CONFIG_PATH))

def get_prompt(prompt_category: str, prompt_name: str) -> str:
    """
    Load a prompt template by category and name from the YAML configuration file.

    :param prompt_category: The category under which the prompt is stored (e.g., 'prompts').
    :param prompt_name: The name of the prompt to load within that category.
    :return: The prompt template as a string.
    """
    try:
        # Verify the configuration file exists
        config_path = Path(PROMPT_CONFIG_PATH)
        if not config_path.exists():
            raise FileNotFoundError(f"Prompt configuration file not found at: {PROMPT_CONFIG_PATH}")

        # Open and load the YAML configuration file
        with open(config_path, 'r', encoding='utf-8') as file:
            prompts_config = yaml.safe_load(file)
            # Navigate to the desired category and prompt
            if prompt_category in prompts_config and prompt_name in prompts_config[prompt_category]:
                return prompts_config[prompt_category][prompt_name]
            else:
                raise ValueError(f"Prompt '{prompt_name}' not found under category '{prompt_category}' in the configuration.")
    
    except Exception as e:
        raise RuntimeError(f"Failed to load prompt configuration: {str(e)}")


# Example usage for testing purposes
if __name__ == "__main__":
    try:
        prompt = get_prompt("rag_prompt")
        print("Loaded prompt:", prompt)
    except RuntimeError as e:
        print(str(e))
