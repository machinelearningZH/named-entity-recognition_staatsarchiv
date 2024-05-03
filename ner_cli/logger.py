import logging
import os
from dotenv import load_dotenv

load_dotenv()

LOG_PATH = os.environ["ROOT"] + "log/"

if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)


# Adapted from: https://betterstack.com/community/questions/how-to-color-python-logging-output/
class CustomFormatter(logging.Formatter):
    """
    Format and colorize log levels according to severity.
    """

    grey: str = "\x1b[38;21m"
    yellow: str  = "\x1b[33;21m"
    red: str = "\x1b[31;21m"
    bold_red: str = "\x1b[31;1m"
    format_str: str = "\033[1m[ %(levelname)-8s ]\033[0m - [ %(asctime)s ] - %(message)s"

    FORMATS: dict = {
        logging.DEBUG: grey + format_str,
        logging.INFO: grey + format_str,
        logging.WARNING: yellow + format_str,
        logging.ERROR: red + format_str,
        logging.CRITICAL: bold_red + format_str,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_dual_logger(log_level, console_formatter):
    """
    Creates logger for simultaenous logging to console and file.
    File handler must be added after instatiation in order to timestamp log file.
    """
    # Create logger
    if log_level == logging.DEBUG:
        logger = logging.getLogger()
    else:
        logger = logging.getLogger("dual_logger")
    logger.setLevel(log_level)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Create formatter and add to handler
    console_handler.setFormatter(console_formatter)

    # Add console handler to logger
    logger.addHandler(console_handler)

    return logger


def setup_file_logger(log_level):
    """
    Creates file logger.
    File handler must be added after instatiation in order to timestamp log file.
    """
    # Create logger
    logger = logging.getLogger("file_logger")
    logger.setLevel(log_level)

    return logger


if bool(int(os.environ["DEBUG"])):
    log_level = logging.DEBUG
else:
    log_level = logging.INFO

logger = setup_dual_logger(log_level, CustomFormatter())
file_logger = setup_file_logger(log_level)
