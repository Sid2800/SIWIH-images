import logging

logger = logging.getLogger("api_images")

def log_info(message):
    logger.info(message)

def log_warning(message):
    logger.warning(message)

def log_error(message):
    logger.error(message, exc_info=True)