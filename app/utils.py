from typing import Dict, Any, Optional
import os
from bson import ObjectId
from database.database import db_manager
from logger import setup_logger
import base64
from io import BytesIO
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from config.settings import settings

logger = setup_logger(__name__)

class Utility:
    def __init__(self):
        pass

    async def _process_and_store_charts(
       self, 
       tool_result: Dict[str, Any], 
       session_id: str, 
       user_id: str, 
       message_id: str
):
        """Extract chart_base64 data and store in GridFS, replace with chart_id"""
        chart_fields = ["chart_base64", "chart", "visualization"]
        
        for field in chart_fields:
            if field in tool_result and tool_result[field]:
                try:
                    chart_data = tool_result[field]
                    
                    # Handle different chart data formats
                    if isinstance(chart_data, str):
                        if chart_data.startswith('data:image'):
                            # Extract base64 data from data URL
                            chart_base64 = chart_data.split(',')[1]
                        else:
                            chart_base64 = chart_data
                    else:
                        continue
                    
                    # Decode base64 to bytes
                    chart_bytes = base64.b64decode(chart_base64)
                    
                    # Create metadata for GridFS
                    metadata = {
                        "session_id": session_id,
                        "user_id": user_id,
                        "message_id": message_id,
                        "content_type": "image/png",
                        "created_at": ObjectId().generation_time
                    }
                    
                    # Store in GridFS
                    chart_id = await self._store_chart_in_gridfs(chart_bytes, "chart.png", metadata)
                    
                    if chart_id:
                        # Store chart info in Chart_Image collection
                        chart_doc = {
                            "user_id": user_id,
                            "session_id": session_id,
                            "message_id": message_id,
                            "image_id": chart_id,
                            "created_at": ObjectId().generation_time
                        }
                        
                        chart_collection = db_manager.database.Chart_Image
                        await chart_collection.insert_one(chart_doc)
                        
                        logger.info(f"Stored chart for with GridFS ID: {chart_id}")
                    
                    # Remove chart_base64 from tool_result
                    del tool_result[field]
                    
                except Exception as e:
                    logger.error(f"Error processing chart data: {str(e)}")
                    # Remove the chart data even if storage fails
                    if field in tool_result:
                        del tool_result[field]

    async def _store_chart_in_gridfs(self, chart_bytes: bytes, filename: str, metadata: Dict[str, Any]) -> Optional[ObjectId]:
        """Store chart data in GridFS and return the file ID"""
        try:
            chart_stream = BytesIO(chart_bytes)
            chart_id = await db_manager.fs_bucket.upload_from_stream(
                filename,
                chart_stream,
                metadata=metadata
            )
            return chart_id
        except Exception as e:
            logger.error(f"Error storing chart in GridFS: {str(e)}")
            return None


    async def select_language(self, user_id: str, session_id: str, language: str):
        try:
            languages = settings.SUPPORTED_LANGUAGES
            if language not in languages:
                logger.warning(f"Unsupported language selected: {language}")
                raise HTTPException(status_code=400, detail=f"Language '{language}' is not supported")
            
            set_language_data = await db_manager.database.LanguagePreference.find_one(
                {"user_id": user_id, "session_id": session_id}
            )
            if not set_language_data:
                set_language_data = {"user_id": user_id, "session_id": session_id, "selected_language": language}
                await db_manager.database.LanguagePreference.insert_one(set_language_data)
            else:
                await db_manager.database.LanguagePreference.update_one(
                    {"user_id": user_id, "session_id": session_id},
                    {"$set": {"selected_language": language}}
                )
            return JSONResponse(
                {"success": True, "message": f"Language '{language}' selected successfully"}
            )
        except Exception as e:
            logger.error(f"Error selecting language: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")


    async def get_chart_base64(self, request):
        try:
            session_id = request.session_id
            user_id = request.user_id
            
            if not session_id or not user_id:
                return {"success": False, "error": "session_id and user_id are required"}
            
            # Fetch the conversation document from MongoDB
            collection = db_manager.database.ChatHistory
            conversation_doc = await collection.find_one({
                "session_id": session_id, 
                "user_id": user_id
            })
            
            if not conversation_doc:
                return {"success": False, "message": "No conversation found for the given session_id and user_id"}
            
            # Extract message_ids from the messages array
            messages = conversation_doc.get("messages", [])
            unique_message_ids = []
            
            for message in messages:
                message_id = message.get("message_id")
                if message_id:
                    unique_message_ids.append(message_id)
            
            # Remove duplicates while preserving order
            unique_message_ids = list(dict.fromkeys(unique_message_ids))
            
            if not unique_message_ids:
                return {"success": False, "message": "No message IDs found in the conversation"}
            
            # Check for chart files and convert to base64
            charts_list = []
            charts_folder = "charts"
            
            for message_id in unique_message_ids:
                chart_path = os.path.join(charts_folder, f"{message_id}.png")
                
                if os.path.exists(chart_path):
                    try:
                        with open(chart_path, "rb") as image_file:
                            base64_string = base64.b64encode(image_file.read()).decode('utf-8')
                            charts_list.append({
                                "message_id": message_id,
                                "chart_data": base64_string,
                                "filename": f"{message_id}.png"
                            })
                    except Exception as file_error:
                        print(f"Error reading chart file {chart_path}: {str(file_error)}")
                        continue
            
            if not charts_list:
                return {"success": False, "message": "No charts available to download"}
            
            return {
                "success": True,
                "session_id": session_id,
                "user_id": user_id,
                "charts_count": len(charts_list),
                "charts": charts_list
            }
        except Exception as e:
            logger.error(f"Error getting chart base64: {str(e)}")
            return {"success": False, "error": "Internal server error"}