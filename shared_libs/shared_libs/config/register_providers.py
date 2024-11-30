# shared_libs/config/register_providers.py

from shared_libs.config.provider_registry import ProviderRegistry

# Register providers with their module paths and class names
ProviderRegistry.register_provider("bedrock", "shared_libs.config.provider_configs", "BedrockEmbeddingConfig")
ProviderRegistry.register_provider("local", "shared_libs.config.provider_configs", "LocalEmbeddingConfig")
# ProviderRegistry.register_provider("openai_embedding", "shared_libs.config.provider_configs", "OpenAIEmbeddingConfig")
# ProviderRegistry.register_provider("google_gemini_embedding", "shared_libs.config.provider_configs", "GoogleGeminiEmbeddingConfig")
# ProviderRegistry.register_provider("docker", "shared_libs.config.provider_configs", "DockerEmbeddingConfig")
ProviderRegistry.register_provider("ec2", "shared_libs.config.provider_configs", "EC2EmbeddingConfig")
# ProviderRegistry.register_provider("genai", "shared_libs.config.provider_configs", "GenAIEmbeddingConfig")
# ProviderRegistry.register_provider("fastembed", "shared_libs.config.provider_configs", "FastEmbedEmbeddingConfig")
