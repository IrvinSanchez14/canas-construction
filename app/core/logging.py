import logging
import sys
from typing import Any, Dict
from app.core.config import settings

# CloudWatch logging for AWS
try:
    import watchtower
    CLOUDWATCH_AVAILABLE = True
except ImportError:
    CLOUDWATCH_AVAILABLE = False


class AppLogger:
    """Centralized logging configuration for AWS CloudWatch integration."""

    @staticmethod
    def setup_logging() -> logging.Logger:
        """Configure logging with CloudWatch handler for AWS environments."""
        logger = logging.getLogger("canas_construction")
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

        # Clear existing handlers
        logger.handlers.clear()

        # Console handler for all environments
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

        # Format for structured logging
        formatter = logging.Formatter(
            '{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", '
            '"message": "%(message)s", "environment": "' + settings.ENVIRONMENT + '"}'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Add CloudWatch handler in production if available
        if settings.is_production and CLOUDWATCH_AVAILABLE:
            try:
                cloudwatch_handler = watchtower.CloudWatchLogHandler(
                    log_group=f"/aws/fastapi/{settings.APP_NAME}",
                    stream_name=f"{settings.ENVIRONMENT}",
                )
                cloudwatch_handler.setFormatter(formatter)
                logger.addHandler(cloudwatch_handler)
            except Exception as e:
                logger.warning(f"Failed to setup CloudWatch logging: {e}")

        return logger


def get_logger(name: str = "canas_construction") -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)
