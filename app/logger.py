import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import traceback
import sys

class CustomFormatter(logging.Formatter):
    """Custom formatter that includes timestamp, filename, function name, line number, and log level"""
    
    def format(self, record):
        # Add timestamp
        record.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Add filename, function name, and line number
        if hasattr(record, 'funcName'):
            record.function_info = f"{record.filename}:{record.funcName}:{record.lineno}"
        else:
            record.function_info = f"{record.filename}:{record.lineno}"
        
        return super().format(record)

def setup_logger(name: str = None, log_level: str = "INFO") -> logging.Logger:
    """
    Setup and return a configured logger
    
    Args:
        name: Logger name (usually __name__)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Get logger
    logger = logging.getLogger(name or __name__)
    
    # Avoid adding handlers if they already exist
    if logger.handlers:
        return logger
    
    # Set log level
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatters
    detailed_formatter = CustomFormatter(
        fmt='%(timestamp)s | %(levelname)-8s | %(function_info)-30s | %(message)s'
    )
    
    console_formatter = CustomFormatter(
        fmt='%(timestamp)s | %(levelname)-8s | %(name)-20s | %(message)s'
    )
    
    # Create handlers
    # File handler with rotation
    file_handler = RotatingFileHandler(
        filename=os.path.join(logs_dir, f"{name or 'app'}.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def log_exception(logger: logging.Logger, exception: Exception, context: str = ""):
    """
    Log an exception with full traceback and context
    
    Args:
        logger: Logger instance
        exception: Exception to log
        context: Additional context information
    """
    error_msg = f"Exception in {context}: {str(exception)}"
    logger.error(error_msg, exc_info=True)

def log_function_entry(logger: logging.Logger, function_name: str = None, **kwargs):
    """
    Log function entry with parameters
    
    Args:
        logger: Logger instance
        function_name: Name of the function (optional, will be auto-detected)
        **kwargs: Function parameters to log
    """
    if not function_name:
        # Try to get function name from stack
        try:
            function_name = sys._getframe(1).f_code.co_name
        except:
            function_name = "unknown_function"
    
    params_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()]) if kwargs else "no parameters"
    logger.debug(f"Entering {function_name} with parameters: {params_str}")

def log_function_exit(logger: logging.Logger, function_name: str = None, result: any = None):
    """
    Log function exit with result
    
    Args:
        logger: Logger instance
        function_name: Name of the function (optional, will be auto-detected)
        result: Function result to log
    """
    if not function_name:
        # Try to get function name from stack
        try:
            function_name = sys._getframe(1).f_code.co_name
        except:
            function_name = "unknown_function"
    
    if result is not None:
        logger.debug(f"Exiting {function_name} with result: {result}")
    else:
        logger.debug(f"Exiting {function_name}")

# Create a default logger for general use
default_logger = setup_logger("app")

