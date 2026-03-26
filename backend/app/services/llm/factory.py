from app.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.openai_provider import OpenAIProvider


def create_llm_provider(provider: str | None = None) -> LLMProvider:
    provider = provider or settings.llm_provider
    if provider == "openai":
        return OpenAIProvider()
    return AnthropicProvider()
