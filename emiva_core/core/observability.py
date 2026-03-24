import phoenix as px
from openinference.instrumentation.langchain import LangChainInstrumentor
from emiva_core.core.logger import setup_logger
from emiva_core.core.settings import settings

logger = setup_logger(__name__)

def setup_observability():
    """ Initializes Arize Phoenix for local LLM tracing if enabled. """
    if not settings.enable_phoenix:
        logger.info("Arize Phoenix observability is disabled.")
        return

    try:
        # Start the local Phoenix session/server
        session = px.launch_app()
        logger.info(f"Arize Phoenix started. Dashboard available at {session.url}")

        # Instrument LangChain to send traces to Phoenix
        LangChainInstrumentor().instrument()
        logger.info("LangChain successfully instrumented for Arize Phoenix.")
        
    except Exception as e:
        logger.error(f"Failed to setup Arize Phoenix observability: {e}")
