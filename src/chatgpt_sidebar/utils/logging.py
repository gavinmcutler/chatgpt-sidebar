"""Logging configuration for ChatGPT Sidebar."""

import logging
from typing import Optional


logger = logging.getLogger(__name__)


def setup_logging(enable_logging: bool = False, log_file: Optional[str] = None) -> None:
    """Setup logging configuration.
    
    Args:
        enable_logging: Whether to enable logging to console and file
        log_file: Path to log file (defaults to 'chatgpt_sidebar.log')
    """
    if log_file is None:
        log_file = 'chatgpt_sidebar.log'
    
    if enable_logging:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file, mode='a')
            ]
        )
        logger.info("Logging enabled")
    else:
        # Disable all logging by setting level to CRITICAL
        logging.disable(logging.CRITICAL)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.
    
    Args:
        name: The logger name (typically __name__)
        
    Returns:
        logging.Logger: A configured logger instance
    """
    return logging.getLogger(name)

