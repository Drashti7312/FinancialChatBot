import asyncio
from typing import List
from datetime import datetime
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from database.database import db_manager
from logger import setup_logger, log_exception, log_function_entry, log_function_exit

logger = setup_logger(__name__)


class MongoDBChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str, user_id: str):
        log_function_entry(logger, "__init__", session_id=session_id, user_id=user_id)
        self.session_id = session_id
        self.user_id = user_id
        self.collection = db_manager.database.ChatHistory
        logger.debug(f"Initialized chat history for session_id={session_id}, user_id={user_id}")
        log_function_exit(logger, "__init__")

    async def aget_messages(self) -> List[BaseMessage]:
        """Retrieve messages from MongoDB"""
        log_function_entry(logger, "aget_messages", session_id=self.session_id, user_id=self.user_id)
        
        try:
            doc = await self.collection.find_one({
                "session_id": self.session_id,
                "user_id": self.user_id
            })

            if not doc or not doc.get("messages"):
                logger.warning(f"No messages found for session_id={self.session_id}, user_id={self.user_id}")
                log_function_exit(logger, "aget_messages", result="no_messages")
                return []

            messages = []
            for msg in doc["messages"]:
                if msg["type"] == "human":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["type"] == "ai":
                    messages.append(AIMessage(content=msg["content"]))

            logger.info(f"Retrieved {len(messages)} messages for session_id={self.session_id}")
            log_function_exit(logger, "aget_messages", result=f"messages_count={len(messages)}")
            return messages
            
        except Exception as e:
            log_exception(logger, e, f"aget_messages - session_id: {self.session_id}, user_id: {self.user_id}")
            log_function_exit(logger, "aget_messages", result="error")
            return []

    def get_messages(self) -> List[BaseMessage]:
        """Sync version of get_messages"""
        log_function_entry(logger, "get_messages")
        try:
            result = asyncio.run(self.aget_messages())
            log_function_exit(logger, "get_messages", result="sync_completed")
            return result
        except Exception as e:
            log_exception(logger, e, "get_messages")
            log_function_exit(logger, "get_messages", result="error")
            return []

    async def aadd_message(self, message: BaseMessage, message_uuid) -> None:
        """Add message to MongoDB"""
        message_type = "human" if isinstance(message, HumanMessage) else "ai"
        log_function_entry(logger, "aadd_message", session_id=self.session_id, user_id=self.user_id, message_type=message_type, message_uuid=message_uuid)
        
        try:
            msg_dict = {
                "type": message_type,
                "content": message.content,
                "timestamp": datetime.now(),
                "message_id": message_uuid
            }

            await self.collection.update_one(
                {"session_id": self.session_id, "user_id": self.user_id},
                {
                    "$push": {"messages": msg_dict},
                    "$set": {"updated_at": datetime.now()},
                    "$setOnInsert": {"created_at": datetime.now()}
                },
                upsert=True
            )
            logger.info(f"Message successfully added to database for session_id={self.session_id}")
            log_function_exit(logger, "aadd_message", result="message_added")
            
        except Exception as e:
            log_exception(logger, e, f"aadd_message - session_id: {self.session_id}, user_id: {self.user_id}, message_type: {message_type}")
            log_function_exit(logger, "aadd_message", result="error")
            raise

    def add_message(self, message: BaseMessage) -> None:
        """Sync version of add_message"""
        log_function_entry(logger, "add_message")
        try:
            asyncio.run(self.aadd_message(message))
            log_function_exit(logger, "add_message", result="sync_completed")
        except Exception as e:
            log_exception(logger, e, "add_message")
            log_function_exit(logger, "add_message", result="error")
            raise

    async def aclear(self) -> None:
        """Clear chat history"""
        log_function_entry(logger, "aclear", session_id=self.session_id, user_id=self.user_id)
        
        try:
            logger.warning(f"Clearing chat history for session_id={self.session_id}, user_id={self.user_id}")
            await self.collection.update_one(
                {"session_id": self.session_id, "user_id": self.user_id},
                {"$set": {"messages": [], "updated_at": datetime.now()}}
            )
            logger.info("Chat history cleared successfully")
            log_function_exit(logger, "aclear", result="history_cleared")
            
        except Exception as e:
            log_exception(logger, e, f"aclear - session_id: {self.session_id}, user_id: {self.user_id}")
            log_function_exit(logger, "aclear", result="error")
            raise

    def clear(self) -> None:
        """Sync version of clear"""
        log_function_entry(logger, "clear")
        try:
            asyncio.run(self.aclear())
            log_function_exit(logger, "clear", result="sync_completed")
        except Exception as e:
            log_exception(logger, e, "clear")
            log_function_exit(logger, "clear", result="error")
            raise
