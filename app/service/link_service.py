from datetime import datetime
from database.database import db_manager
from logger import setup_logger, log_exception, log_function_entry, log_function_exit

logger = setup_logger(__name__)

class LinkService:
    """Service for handling link operations"""
    
    @staticmethod
    async def add_link(session_id: str, user_id: str, url: str, title: str = None) -> str:
        """Add link to database if not already present"""
        log_function_entry(logger, "add_link", session_id=session_id, user_id=user_id, url=url, title=title)
        
        try:
            # Check if link already exists for the same session & user
            existing_link = await db_manager.database.links.find_one({
                "session_id": session_id,
                "user_id": user_id,
                "url": url
            })

            if existing_link:
                logger.warning(f"Duplicate link attempt: {url} | Session: {session_id} | User: {user_id}")
                log_function_exit(logger, "add_link", result="duplicate_link")
                raise ValueError("Link already present")

            link_doc = {
                "session_id": session_id,
                "user_id": user_id,
                "url": url,
                "title": title or url,
                "created_at": datetime.now()
            }
            
            result = await db_manager.database.links.insert_one(link_doc)
            link_id = str(result.inserted_id)
            
            logger.info(f"Link added successfully: {url} | Link ID: {link_id} | Session: {session_id} | User: {user_id}")
            log_function_exit(logger, "add_link", result=f"link_id={link_id}")
            return link_id
        
        except ValueError:
            # Explicitly re-raise so caller can handle the duplicate case
            log_function_exit(logger, "add_link", result="value_error")
            raise
        except Exception as e:
            log_exception(logger, e, f"add_link - url: {url}, session_id: {session_id}, user_id: {user_id}")
            log_function_exit(logger, "add_link", result="error")
            raise
