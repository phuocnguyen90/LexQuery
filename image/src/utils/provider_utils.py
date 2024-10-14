# src/utils/provider_utils.py
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from providers.groq_provider import GroqProvider
from load_config import ConfigLoader

# Singleton GroqProvider initialization
config = ConfigLoader().get_config()
groq_provider = GroqProvider(config=config.get('groq', {}))

def get_groq_provider():
    return groq_provider
