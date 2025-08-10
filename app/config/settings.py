import os
from pydantic_settings import BaseSettings
from typing import List
from logger import setup_logger, log_exception, log_function_entry, log_function_exit

logger = setup_logger(__name__)

class Settings(BaseSettings):
    MONGODB_URL: str = os.getenv("MONGODB_URL")
    MONGODB_DB_NAME: str = "financial_chatbot"
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")
    GOOGLE_GEMINI_MODEL: str = "gemini-1.5-flash"
    
    NEXT_PUBLIC_API_BASE: str = os.getenv("NEXT_PUBLIC_API_BASE")
    NEXT_PUBLIC_DEFAULT_USER_ID: str = os.getenv("NEXT_PUBLIC_DEFAULT_USER_ID")

    SUPPORTED_EXTENSIONS: List[str] = ['csv', 'xlsx', 'xls', 'pdf', 'docx']

    SUPPORTED_LANGUAGES: List[str] = [
        "English", 
        "Spanish", 
        "French", 
        "German", 
        "Italian", 
        "Portuguese", 
        "Dutch", 
        "Russian",
        "Chinese",
        "Japanese",
        "Korean",
        "Arabic",
        "Hindi",
        "Gujarati",
        "Marathi"
    ]
    class Config:
        env_file = ".env"

    def __init__(self, **kwargs):
        log_function_entry(logger, "__init__", **kwargs)
        try:
            super().__init__(**kwargs)
            logger.info("Settings initialized successfully")
            log_function_exit(logger, "__init__", result="initialization_successful")
        except Exception as e:
            log_exception(logger, e, "Settings initialization")
            log_function_exit(logger, "__init__", result="initialization_failed")
            raise

settings = Settings()