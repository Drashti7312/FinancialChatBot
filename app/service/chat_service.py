from typing import Any, List, Dict
from core.chat_history import MongoDBChatMessageHistory
from core.tool_orchestrator import orchestrator
from service.document_service import DocumentService
from database.database import db_manager
from langchain_core.messages import HumanMessage, AIMessage
from logger import setup_logger, log_exception, log_function_entry, log_function_exit
import uuid


logger = setup_logger(__name__)


class ChatService:
    """Service for handling chat operations"""

    @staticmethod
    async def process_chat(session_id: str, user_id: str, message: str) -> str:
        """Process chat message and return response"""
        log_function_entry(logger, "process_chat", session_id=session_id, user_id=user_id, message_length=len(message))
        
        try:
            # Get chat history
            message_uuid = str(uuid.uuid4())
            logger.debug(f"Generated message_uuid={message_uuid} for session_id={session_id}")
            chat_history = MongoDBChatMessageHistory(session_id, user_id)
            logger.debug(f"Chat history instance created for session_id={session_id}, user_id={user_id}")

            # Add user message to history
            user_msg = HumanMessage(content=message)
            await chat_history.aadd_message(user_msg, message_uuid)
            logger.info("User message saved to chat history")

            # Get session documents
            session_docs = await DocumentService.get_session_documents(session_id, user_id)
            logger.info(f"Fetched session documents for session_id={session_id}: {session_docs}")

            documents_dict = {}
            if session_docs:
                documents_dict = {
                    "csv_ids": session_docs.csv_ids,
                    "excel_ids": session_docs.excel_ids,
                    "pdf_ids": session_docs.pdf_ids,
                    "docx_ids": session_docs.docx_ids,
                    "link_ids": session_docs.link_ids
                }
                logger.debug(f"Document dictionary prepared: {documents_dict}")

            # Process query with orchestrator
            logger.info(f"Sending query to orchestrator for session_id={session_id}")
            response = await orchestrator.process_query(
                session_id, user_id, message, message_uuid, documents_dict
            )
            logger.info(f"Received orchestrator response: {response}")

            # Add AI response to history
            ai_msg = AIMessage(content=response)
            await chat_history.aadd_message(ai_msg, message_uuid=message_uuid)
            logger.info("AI response saved to chat history")

            log_function_exit(logger, "process_chat", result="response_generated")
            return response

        except Exception as e:
            log_exception(logger, e, f"process_chat - session_id: {session_id}, user_id: {user_id}")
            log_function_exit(logger, "process_chat", result="error")
            return "I apologize, but I encountered an error while processing your request."

    @staticmethod
    async def get_user_sessions(user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        log_function_entry(logger, "get_user_sessions", user_id=user_id)
        
        try:
            cursor = db_manager.database.ChatHistory.find(
                {"user_id": user_id},
                {"session_id": 1, "created_at": 1, "updated_at": 1}
            ).sort("updated_at", -1)

            sessions = []
            async for doc in cursor:
                sessions.append({
                    "session_id": doc["session_id"],
                    "created_at": doc["created_at"].strftime("%d-%m-%Y"),
                    "updated_at": doc["updated_at"].strftime("%d-%m-%Y")
                })

            logger.info(f"Found {len(sessions)} sessions for user_id={user_id}")
            log_function_exit(logger, "get_user_sessions", result=f"sessions_count={len(sessions)}")
            return sessions

        except Exception as e:
            log_exception(logger, e, f"get_user_sessions - user_id: {user_id}")
            log_function_exit(logger, "get_user_sessions", result="error")
            return []

    @staticmethod
    async def get_session_chat(session_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a session directly from DB (messages array)"""
        log_function_entry(logger, "get_session_chat", session_id=session_id, user_id=user_id)
        
        try:
            doc = await db_manager.database.ChatHistory.find_one(
                {"session_id": session_id, "user_id": user_id},
                {"_id": 0, "messages": 1}
            )

            if not doc or "messages" not in doc:
                logger.warning(f"No messages found for session_id={session_id}, user_id={user_id}")
                log_function_exit(logger, "get_session_chat", result="no_messages_found")
                return []

            # Format timestamps as strings if needed
            messages = [
                {
                    "type": msg["type"],
                    "content": msg["content"],
                    "timestamp": msg["timestamp"].strftime("%d-%m-%Y %H:%M:%S")
                    if hasattr(msg["timestamp"], "strftime") else msg["timestamp"]
                }
                for msg in doc["messages"]
            ]

            logger.info(f"Retrieved {len(messages)} messages for session_id={session_id}")
            log_function_exit(logger, "get_session_chat", result=f"messages_count={len(messages)}")
            return messages

        except Exception as e:
            log_exception(logger, e, f"get_session_chat - session_id: {session_id}, user_id: {user_id}")
            log_function_exit(logger, "get_session_chat", result="error")
            return []
