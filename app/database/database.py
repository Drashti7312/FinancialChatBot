from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from typing import Optional
from config.settings import settings
from logger import setup_logger, log_exception, log_function_entry, log_function_exit

logger = setup_logger(__name__)

class DatabaseManager:
    def __init__(self):
        log_function_entry(logger, "__init__")
        self.client: Optional[AsyncIOMotorClient] = None
        self.database = None
        self.fs_bucket = None
        log_function_exit(logger, "__init__")
        
    async def connect_to_mongo(self):
        """Create database connection"""
        log_function_entry(logger, "connect_to_mongo", mongodb_url=settings.MONGODB_URL, db_name=settings.MONGODB_DB_NAME)
        
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.database = self.client[settings.MONGODB_DB_NAME]
            self.fs_bucket = AsyncIOMotorGridFSBucket(self.database)
            logger.info("Connected to MongoDB successfully")
            log_function_exit(logger, "connect_to_mongo", result="connection_established")
            
        except Exception as e:
            log_exception(logger, e, f"connect_to_mongo - mongodb_url: {settings.MONGODB_URL}, db_name: {settings.MONGODB_DB_NAME}")
            log_function_exit(logger, "connect_to_mongo", result="connection_failed")
            raise
        
    async def close_mongo_connection(self):
        """Close database connection"""
        log_function_entry(logger, "close_mongo_connection")
        
        try:
            if self.client:
                self.client.close()
                logger.info("Disconnected from MongoDB successfully")
                log_function_exit(logger, "close_mongo_connection", result="disconnection_successful")
            else:
                logger.warning("No MongoDB connection to close")
                log_function_exit(logger, "close_mongo_connection", result="no_connection_to_close")
                
        except Exception as e:
            log_exception(logger, e, "close_mongo_connection")
            log_function_exit(logger, "close_mongo_connection", result="disconnection_failed")
            raise

# Global database manager instance
db_manager = DatabaseManager()
