from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from contextlib import asynccontextmanager
from database.database import db_manager
from mcp.mcp_server import mcp_server
from config.settings import settings
from schema.models import LinkUpload, ChatMessage, GetChartsRequest
from service.document_service import DocumentService
from service.link_service import LinkService
from service.chat_service import ChatService
from logger import setup_logger, log_exception, log_function_entry, log_function_exit
import sys
from app.utility import Utility
from fastapi.middleware.cors import CORSMiddleware

# Setup logging
logger = setup_logger(__name__)

@asynccontextmanager
async def lifespan(
    app: FastAPI
):
    """Application lifespan manager"""
    log_function_entry(logger, "lifespan", app_title=app.title)
    
    try:
        # Startup
        logger.info("Starting application startup sequence")
        await db_manager.connect_to_mongo()
        
        # Save MCP configuration
        mcp_server.save_config()
        
        logger.info("Financial Intelligence Chatbot started successfully")
        log_function_exit(logger, "lifespan", result="startup_completed")
        
    except Exception as e:
        log_exception(logger, e, "Application startup")
        raise
    else:
        yield
    finally:
        # Shutdown
        try:
            logger.info("Starting application shutdown sequence")
            await db_manager.close_mongo_connection()
            logger.info("Application shutdown completed")
        except Exception as e:
            log_exception(logger, e, "Application shutdown")

app = FastAPI(
    title="Financial Intelligence Chatbot",
    description="AI-powered financial document analysis and chat system",
    version="1.0.0",
    lifespan=lifespan
)
origins = [
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root page"""
    log_function_entry(logger, "root")
    try:
        response = """
        <html>
            <head>
                <title>Financial Intelligence Chatbot</title>
            </head>
            <body style="font-family: Arial, sans-serif; margin: 40px;">
                <h1>💬 Financial Intelligence Chatbot</h1>
                <p>Welcome! This API provides AI-powered financial document analysis and chat features.</p>
                <h3>Available Endpoints</h3>
                <ul>
                    <li><a href="/docs">Swagger UI Documentation</a></li>
                    <li><a href="/api/v1/health">Health Check</a></li>
                    <li><a href="/api/v1/tools">Available Tools</a></li>
                </ul>
            </body>
        </html>
        """
        log_function_exit(logger, "root", result="HTML_response_returned")
        return response
    except Exception as e:
        log_exception(logger, e, "root endpoint")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/upload")
async def upload_document(
    session_id: str,
    user_id: str,
    file: UploadFile = File(...)
):
    """Upload a document (CSV, Excel, PDF, DOCX)"""
    log_function_entry(logger, "upload_document", session_id=session_id, user_id=user_id, filename=file.filename if file else None)
    
    try:
        if not file.filename:
            logger.warning("Upload attempt with no filename")
            raise HTTPException(status_code=400, detail="No file uploaded")

        # Extract and validate extension
        file_extension = file.filename.rsplit('.', 1)[-1].lower()
        logger.debug(f"File extension detected: {file_extension}")
        
        if file_extension not in settings.SUPPORTED_EXTENSIONS:
            logger.warning(f"Unsupported file type attempted: {file_extension}")
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{file_extension}'. "
                       f"Supported types: {', '.join(settings.SUPPORTED_EXTENSIONS)}"
            )

        # Read file data
        file_data = await file.read()
        if not file_data:
            logger.warning("Empty file uploaded")
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        # Normalize file type
        type_mapping = {
            "xlsx": "excel",
            "xls": "excel"
        }
        file_type = type_mapping.get(file_extension, file_extension)
        logger.debug(f"Normalized file type: {file_type}")

        # Upload document
        file_id = await DocumentService().upload_document(
            session_id=session_id,
            user_id=user_id,
            file_data=file_data,
            filename=file.filename,
            file_type=file_type
        )

        logger.info(
            f"File uploaded successfully: {file.filename} | Session: {session_id} | User: {user_id} | File ID: {file_id}"
        )

        response_data = {
            "success": True,
            "file_id": file_id,
            "message": f"File '{file.filename}' uploaded successfully"
        }
        
        log_function_exit(logger, "upload_document", result=f"file_id={file_id}")
        return JSONResponse(response_data)

    except HTTPException:
        log_function_exit(logger, "upload_document", result="HTTP_exception_raised")
        raise
    except ValueError as ve:
        logger.warning(f"Duplicate upload attempt: {file.filename} | Session: {session_id} | User: {user_id}")
        log_function_exit(logger, "upload_document", result="duplicate_upload_error")
        raise HTTPException(status_code=409, detail=str(ve))
    except Exception as e:
        log_exception(logger, e, f"upload_document - filename: {file.filename if file else 'unknown'}, session: {session_id}, user: {user_id}")
        log_function_exit(logger, "upload_document", result="unexpected_error")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/add-link")
async def add_link(
    request: LinkUpload
):
    """Add a web link for analysis"""
    log_function_entry(logger, "add_link", session_id=request.session_id, user_id=request.user_id, url=request.url)
    
    try:
        link_id = await LinkService().add_link(
            request.session_id, request.user_id, request.url, request.title
        )
        
        logger.info(f"Link added successfully: {request.url} | Session: {request.session_id} | User: {request.user_id} | Link ID: {link_id}")
        
        response_data = {
            "success": True,
            "link_id": link_id,
            "message": "Link added successfully"
        }
        
        log_function_exit(logger, "add_link", result=f"link_id={link_id}")
        return JSONResponse(response_data)
        
    except Exception as e:
        log_exception(logger, e, f"add_link - url: {request.url}, session: {request.session_id}, user: {request.user_id}")
        log_function_exit(logger, "add_link", result="error")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/chat")
async def chat(
    request: ChatMessage
):
    """Process chat message"""
    log_function_entry(logger, "chat", session_id=request.session_id, user_id=request.user_id, message_length=len(request.message))
    
    try:
        response = await ChatService.process_chat(
            request.session_id, request.user_id, request.message
        )
        
        logger.info(f"Chat processed successfully: Session: {request.session_id} | User: {request.user_id} | Response length: {len(response) if response else 0}")
        
        response_data = {
            "success": True,
            "response": response
        }
        
        log_function_exit(logger, "chat", result="response_generated")
        return JSONResponse(response_data)
        
    except Exception as e:
        log_exception(logger, e, f"chat - session: {request.session_id}, user: {request.user_id}")
        log_function_exit(logger, "chat", result="error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sessions/{user_id}")
async def get_user_sessions(
    user_id: str
):
    """Get all sessions for a user"""
    log_function_entry(logger, "get_user_sessions", user_id=user_id)
    
    try:
        sessions = await ChatService().get_user_sessions(user_id)
        
        logger.info(f"Retrieved {len(sessions)} sessions for user: {user_id}")
        
        response_data = {
            "success": True,
            "sessions": sessions
        }
        
        log_function_exit(logger, "get_user_sessions", result=f"sessions_count={len(sessions)}")
        return JSONResponse(response_data)
        
    except Exception as e:
        log_exception(logger, e, f"get_user_sessions - user_id: {user_id}")
        log_function_exit(logger, "get_user_sessions", result="error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/chat/{session_id}/{user_id}")
async def get_session_chat(
    session_id: str,
    user_id: str
):
    """Get chat history for a session"""
    log_function_entry(logger, "get_session_chat", session_id=session_id, user_id=user_id)
    
    try:
        messages = await ChatService().get_session_chat(session_id, user_id)
        
        logger.info(f"Retrieved {len(messages)} messages for session: {session_id} | User: {user_id}")
        
        response_data = {
            "success": True,
            "messages": messages
        }
        
        log_function_exit(logger, "get_session_chat", result=f"messages_count={len(messages)}")
        return JSONResponse(response_data)
        
    except Exception as e:
        log_exception(logger, e, f"get_session_chat - session_id: {session_id}, user_id: {user_id}")
        log_function_exit(logger, "get_session_chat", result="error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    log_function_entry(logger, "health_check")
    
    try:
        response_data = {"status": "healthy", "service": "Financial Intelligence Chatbot"}
        log_function_exit(logger, "health_check", result="healthy")
        return response_data
    except Exception as e:
        log_exception(logger, e, "health_check")
        log_function_exit(logger, "health_check", result="error")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.get("/api/v1/tools")
async def get_available_tools():
    """Get list of available MCP tools"""
    log_function_entry(logger, "get_available_tools")
    
    try:
        tools = mcp_server.get_available_tools()
        logger.info(f"Retrieved {len(tools)} available tools")
        
        response_data = {"tools": tools}
        log_function_exit(logger, "get_available_tools", result=f"tools_count={len(tools)}")
        return response_data
    except Exception as e:
        log_exception(logger, e, "get_available_tools")
        log_function_exit(logger, "get_available_tools", result="error")
        raise HTTPException(status_code=500, detail="Failed to retrieve tools")
    

@app.get("/api/v1/supported_languages")
async def get_supported_languages():
    """Get list of supported languages"""
    log_function_entry(logger, "get_supported_languages")

    try:
        languages = settings.SUPPORTED_LANGUAGES
        logger.info(f"Retrieved {len(languages)} supported languages")

        response_data = {"languages": languages}
        log_function_exit(logger, "get_supported_languages", result=f"languages_count={len(languages)}")
        return response_data
    except Exception as e:
        log_exception(logger, e, "get_supported_languages")
        log_function_exit(logger, "get_supported_languages", result="error")
        raise HTTPException(status_code=500, detail="Failed to retrieve languages")
    
@app.post("/api/v1/select_language")
async def select_language(language: str, user_id: str, session_id: str):
    """Select a supported language"""
    log_function_entry(logger, "select_language", language=language)

    try:
        return await Utility().select_language(user_id, session_id, language)
    except Exception as e:
        log_exception(logger, e, "select_language")
        log_function_exit(logger, "select_language", result="error")
        raise HTTPException(status_code=500, detail="Failed to select language")

@app.post("/api/v1/get_charts")
async def get_charts(request: GetChartsRequest):
    try:
        return await Utility().get_chart_base64(request)

    except Exception as e:
        return {"success": False, "error": f"Failed to fetch charts: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Financial Intelligence Chatbot server")
    try:
        uvicorn.run(
            "main:app", 
            host="0.0.0.0", 
            port=8000, 
            reload=True,
            log_level="info"
        )
    except Exception as e:
        log_exception(logger, e, "Server startup")
        sys.exit(1)
