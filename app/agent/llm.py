from functools import lru_cache
from langchain.chat_models import init_chat_model
from app.core.settings import settings
from app.core.llm_providers import Provider
from app.core.logger import setup_logger

logger = setup_logger(__name__)


from langchain_core.callbacks import BaseCallbackHandler


class LlmLoggingHandler(BaseCallbackHandler):
    """
    Custom callback handler to log LLM prompts and responses using the app logger.
    """

    def on_chat_model_start(self, serialized, messages, **kwargs):
        for chunk in messages:
            msg_strs = [f"{m.type}: {m.content}" for m in chunk]
            full_prompt = "\n".join(msg_strs)
            logger.info(f"LLM Request:\n{full_prompt}")

    def on_llm_end(self, response, **kwargs):
        for generation in response.generations:
            res_text = generation[0].text
            logger.info(f"LLM Response:\n{res_text}")


def _build_llm(provider: Provider):
    """
    Builds and returns a LangChain BaseChatModel for the given provider.
    Called lazily — not at import time.
    """
    callbacks = [LlmLoggingHandler()]

    if provider == Provider.OPENAI:
        return init_chat_model(
            model=settings.llm_model_name,
            model_provider=provider.value,
            temperature=settings.temperature,
            api_key=settings.openai_api_key,
            callbacks=callbacks,
        )
    elif provider == Provider.ANTHROPIC:
        return init_chat_model(
            model=settings.llm_model_name,
            model_provider=provider.value,
            temperature=settings.temperature,
            api_key=settings.anthropic_api_key,
            callbacks=callbacks,
        )
    elif provider == Provider.GROQ:
        return init_chat_model(
            model=settings.llm_model_name,
            model_provider=provider.value,
            temperature=settings.temperature,
            api_key=settings.groq_api_key,
            callbacks=callbacks,
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
