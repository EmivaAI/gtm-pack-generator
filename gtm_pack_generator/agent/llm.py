from functools import lru_cache
from langchain.chat_models import init_chat_model
from gtm_pack_generator.core.settings import settings
from gtm_pack_generator.core.llm_providers import Provider
from gtm_pack_generator.core.logger import setup_logger

logger = setup_logger(__name__)


def _build_llm(provider: Provider):
    """
    Builds and returns a LangChain BaseChatModel for the given provider.
    Called lazily — not at import time.
    """
    if provider == Provider.OPENAI:
        return init_chat_model(
            model=settings.llm_model_name,
            model_provider=provider.value,
            temperature=settings.temperature,
            api_key=settings.openai_api_key,
        )
    elif provider == Provider.ANTHROPIC:
        return init_chat_model(
            model=settings.llm_model_name,
            model_provider=provider.value,
            temperature=settings.temperature,
            api_key=settings.anthropic_api_key,
        )
    elif provider == Provider.GROQ:
        return init_chat_model(
            model=settings.llm_model_name,
            model_provider=provider.value,
            temperature=settings.temperature,
            api_key=settings.groq_api_key,
        )


@lru_cache(maxsize=1)
def get_llm_instance():
    """
    Returns the application-wide LLM instance, created lazily on first call.
    Cached for the lifetime of the process.
    """
    provider = (
        Provider(settings.llm_provider) if settings.llm_provider else Provider.OPENAI
    )
    return _build_llm(provider)
