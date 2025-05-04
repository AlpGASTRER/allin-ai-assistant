import sys
import os
from loguru import logger
# Use relative import to access config within the same package ('core')
from .config import settings

# --- Log Configuration --- #

# Remove default logger
logger.remove()

# Determine log level from settings
log_level = settings.log_level.upper()

# Standard output handler
logger.add(
    sys.stderr, # Log to standard error
    level=log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
    enqueue=True # Make logging asynchronous
)

# Optional file handler
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
    except OSError as e:
        logger.error(f"Could not create log directory: {log_dir}. Error: {e}")
        log_dir = None # Disable file logging if dir creation fails

if log_dir:
    log_file_path = os.path.join(log_dir, "allin_app_{time:YYYY-MM-DD}.log")
    logger.add(
        log_file_path,
        rotation="00:00", # Rotate daily at midnight
        retention="7 days", # Keep logs for 7 days
        compression="zip", # Compress rotated files
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True # Make file logging asynchronous
    )

logger.info(f"Logging configured. Level: {log_level}. File logging to: {log_dir if log_dir else 'Disabled'}")

# --- Example Usage --- #
# In other modules:
# from allin_app.core.logging_config import logger
#
# logger.debug("This is a debug message.")
# logger.info("This is an info message.")
# logger.warning("This is a warning message.")
# logger.error("This is an error message.")
# logger.critical("This is a critical message.")
