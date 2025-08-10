from datetime import datetime
from typing import Optional
from database.database import db_manager
from schema.models import SessionDocuments
from logger import setup_logger, log_exception, log_function_entry, log_function_exit

logger = setup_logger(__name__)

class DocumentService:
    """Service for handling document operations"""
        
    @staticmethod
    async def upload_document(session_id: str, user_id: str, file_data: bytes,
                               filename: str, file_type: str) -> str:
        """Upload document to GridFS and update session documents"""
        log_function_entry(logger, "upload_document", session_id=session_id, user_id=user_id, filename=filename, file_type=file_type, file_size=len(file_data))
        
        try:
            # Query fs.files directly for duplicates
            existing_file = await db_manager.database.fs.files.find_one({
                "filename": filename,
                "metadata.session_id": session_id,
                "metadata.user_id": user_id
            })

            if existing_file:
                logger.warning(f"Duplicate file upload attempted: {filename} | Session: {session_id} | User: {user_id}")
                log_function_exit(logger, "upload_document", result="duplicate_file")
                raise ValueError("File already present")

            # Upload file to GridFS
            file_id = await db_manager.fs_bucket.upload_from_stream(
                filename,
                file_data,
                metadata={"session_id": session_id, "user_id": user_id}
            )
            logger.info(f"File uploaded to GridFS: {filename} | File ID: {file_id}")

            # Update session documents
            type_key = f"{file_type}_ids"
            session_docs = db_manager.database.SessionDocuments

            await session_docs.update_one(
                {"session_id": session_id, "user_id": user_id},
                {
                    "$push": {type_key: str(file_id)},
                    "$setOnInsert": {"created_at": datetime.now()}
                },
                upsert=True
            )
            logger.info(f"Session documents updated for session_id={session_id}, user_id={user_id}")

            log_function_exit(logger, "upload_document", result=f"file_id={file_id}")
            return str(file_id)

        except ValueError:
            log_function_exit(logger, "upload_document", result="value_error")
            raise
        except Exception as e:
            log_exception(logger, e, f"upload_document - filename: {filename}, session_id: {session_id}, user_id: {user_id}")
            log_function_exit(logger, "upload_document", result="error")
            raise
    
    @staticmethod
    async def get_session_documents(session_id: str, user_id: str) -> Optional[SessionDocuments]:
        """Get all documents for a session"""
        log_function_entry(logger, "get_session_documents", session_id=session_id, user_id=user_id)
        
        try:
            doc = await db_manager.database.SessionDocuments.find_one({
                "session_id": session_id,
                "user_id": user_id
            })
            
            if doc:
                session_documents = SessionDocuments(**doc)
                logger.info(f"Retrieved session documents for session_id={session_id}, user_id={user_id}")
                log_function_exit(logger, "get_session_documents", result="documents_found")
                return session_documents
            else:
                logger.info(f"No session documents found for session_id={session_id}, user_id={user_id}")
                log_function_exit(logger, "get_session_documents", result="no_documents")
                return None
            
        except Exception as e:
            log_exception(logger, e, f"get_session_documents - session_id: {session_id}, user_id: {user_id}")
            log_function_exit(logger, "get_session_documents", result="error")
            return None
