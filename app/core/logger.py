import logging
import sys
from pythonjsonlogger import jsonlogger
from app.core.settings import settings


def setup_logger(name: str = "app") -> logging.Logger:
    """
    Configure and return a standard logger.
    Uses JSON formatting in production and standard text in development.
    """
    logger = logging.getLogger(name)

    # Prevent adding multiple handlers if the logger is requested multiple times
    if not logger.handlers:
        # 1. Determine Log Level
        level = logging.INFO if settings.environment == "development" else logging.WARNING
        logger.setLevel(level)

        # 2. Configure Handler
        console_handler = logging.StreamHandler(sys.stdout)

        # 3. Configure Formatter based on environment
        if settings.environment == "development":
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            # Production: Structured JSON
            formatter = jsonlogger.JsonFormatter(
                "%(asctime)s %(name)s %(levelname)s %(message)s"
            )

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


logger = setup_logger()
