import logging
import sys
import os


def setup_logger(name: str = "app") -> logging.Logger:
    """
    Configure and return a standard logger.
    """
    logger = logging.getLogger(name)

    # Prevent adding multiple handlers if the logger is requested multiple times
    if not logger.handlers:
        env = os.getenv("ENVIRONMENT", "development")
        
        # 1. Determine Log Level
        level = logging.INFO if env == "development" else logging.WARNING
        logger.setLevel(level)

        # 2. Configure Handler
        console_handler = logging.StreamHandler(sys.stdout)

        # 3. Configure Formatter based on environment
        if env == "development":
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            # Production: Structured JSON
            from pythonjsonlogger import json
            formatter = json.JsonFormatter(
                "%(asctime)s %(name)s %(levelname)s %(message)s"
            )

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


logger = setup_logger()
