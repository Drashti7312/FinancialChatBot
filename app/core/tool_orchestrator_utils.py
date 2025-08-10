from bson import ObjectId
import base64
import re
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage
from database.database import db_manager
from logger import setup_logger, log_exception, log_function_entry, log_function_exit
from core.multilingual import detect_language_llm

logger = setup_logger(__name__)

class ToolOrchestratorUtils:
    """Utility class for ToolOrchestrator helper methods"""
    
    def __init__(self):
        log_function_entry(logger, "__init__")
        logger.info("ToolOrchestratorUtils initialized successfully")
        log_function_exit(logger, "__init__", result="initialization_successful")
    
    def parse_table_extraction_params(self, query: str) -> Dict[str, Any]:
        """Parse user query to extract table extraction parameters"""
        log_function_entry(logger, "parse_table_extraction_params", query_length=len(query))
        
        try:
            query_lower = query.lower()
            params = {
                "extraction_type": "all",
                "n_results": 10,
                "sort_column": None,
                "ascending": True
            }
            
            # Extract number of results
            number_patterns = [
                r'(?:top|first|show)\s+(\d+)',
                r'(\d+)\s+(?:rows?|records?|entries?)',
                r'limit\s+(\d+)',
                r'(\d+)\s+(?:results?)'
            ]
            
            for pattern in number_patterns:
                match = re.search(pattern, query_lower)
                if match:
                    try:
                        params["n_results"] = int(match.group(1))
                        params["extraction_type"] = "top_n"
                        break
                    except ValueError:
                        pass
            
            # Extract sorting information
            sort_patterns = {
                r'(?:sort|order)\s+by\s+(\w+)': None,
                r'highest\s+(\w+)': False,  # descending
                r'lowest\s+(\w+)': True,   # ascending
                r'largest\s+(\w+)': False,
                r'smallest\s+(\w+)': True,
                r'maximum\s+(\w+)': False,
                r'minimum\s+(\w+)': True,
                r'top\s+.*?by\s+(\w+)': False,
                r'bottom\s+.*?by\s+(\w+)': True
            }
            
            for pattern, ascending in sort_patterns.items():
                match = re.search(pattern, query_lower)
                if match:
                    column_name = match.group(1)
                    params["sort_column"] = column_name
                    if ascending is not None:
                        params["ascending"] = ascending
                        params["extraction_type"] = "top_n"
                    break
            
            # Check for ascending/descending keywords
            if params["sort_column"]:
                if any(word in query_lower for word in ['desc', 'descending', 'highest', 'largest', 'maximum']):
                    params["ascending"] = False
                elif any(word in query_lower for word in ['asc', 'ascending', 'lowest', 'smallest', 'minimum']):
                    params["ascending"] = True
            
            # Extract filter conditions
            filter_patterns = [
                r'where\s+(\w+)\s*([><=!]+)\s*([^\s]+)',
                r'(\w+)\s*([><=!]+)\s*([^\s,]+)',
                r'filter\s+by\s+(\w+)\s*([><=!]+)\s*([^\s]+)'
            ]
            
            filters = []
            for pattern in filter_patterns:
                matches = re.finditer(pattern, query_lower)
                for match in matches:
                    column, operator, value = match.groups()
                    # Try to convert value to appropriate type
                    try:
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        pass  # Keep as string
                    
                    filters.append({
                        "column": column,
                        "operator": operator,
                        "value": value
                    })
            
            if filters:
                params["filters"] = filters
            
            # Common column name mappings
            column_mappings = {
                'sales': ['sales', 'revenue', 'income'],
                'profit': ['profit', 'earnings', 'net_income'],
                'cost': ['cost', 'expense', 'expenditure'],
                'quantity': ['quantity', 'qty', 'amount'],
                'price': ['price', 'cost', 'rate'],
                'date': ['date', 'time', 'timestamp'],
                'name': ['name', 'title', 'product', 'item']
            }
            
            # If no specific column found, try to infer from common terms
            if not params["sort_column"]:
                for canonical, variations in column_mappings.items():
                    for variation in variations:
                        if variation in query_lower:
                            params["sort_column"] = canonical
                            if any(word in query_lower for word in ['top', 'highest', 'maximum', 'best']):
                                params["ascending"] = False
                                params["extraction_type"] = "top_n"
                            break
                    if params["sort_column"]:
                        break
            
            # Set default sort column if extraction type is top_n but no column specified
            if params["extraction_type"] == "top_n" and not params["sort_column"]:
                # Default to common business metrics
                default_columns = ['sales', 'revenue', 'profit', 'amount', 'value']
                params["sort_column"] = default_columns[0]  # Will be validated by the tool
            
            logger.debug(f"Parsed table extraction params: {params}")
            log_function_exit(logger, "parse_table_extraction_params", result=f"params={params}")
            return params
            
        except Exception as e:
            log_exception(logger, e, "parse_table_extraction_params")
            log_function_exit(logger, "parse_table_extraction_params", result="error")
            # Return default params
            return {
                "extraction_type": "top_n",
                "n_results": 10,
                "sort_column": "sales",
                "ascending": False
            }
    
    def convert_tool_result_to_response(self, tool_result: Dict[str, Any], intent: str) -> str:
        """Convert tool result to readable response without heavy formatting"""
        log_function_entry(logger, "convert_tool_result_to_response", intent=intent)
        
        try:
            if not tool_result.get("success", False):
                error_msg = f"Error: {tool_result.get('error', 'Unknown error occurred')}"
                log_function_exit(logger, "convert_tool_result_to_response", result="error_response")
                return error_msg
            
            # Return the raw tool result with minimal formatting
            result_str = ""
            
            # Remove success flag and add key information
            display_result = {k: v for k, v in tool_result.items() if k != "success"}
            
            for key, value in display_result.items():
                if key == "error":
                    continue
                result_str += f"{key}: {value}\n"
            
            response = result_str.strip() if result_str else "Analysis completed successfully."
            log_function_exit(logger, "convert_tool_result_to_response", result="success_response")
            return response
            
        except Exception as e:
            log_exception(logger, e, "convert_tool_result_to_response")
            log_function_exit(logger, "convert_tool_result_to_response", result="error")
            return "Error occurred while processing the response."
    
    def extract_metric_from_query(self, query: str) -> str:
        """Extract financial metric from user query"""
        log_function_entry(logger, "extract_metric_from_query", query_length=len(query))
        
        try:
            query_lower = query.lower()
            metrics = ["revenue", "sales", "profit", "expenses", "income", "cost"]
            
            for metric in metrics:
                if metric in query_lower:
                    logger.debug(f"Extracted metric: {metric}")
                    log_function_exit(logger, "extract_metric_from_query", result=f"metric={metric}")
                    return metric
            
            logger.debug("No specific metric found, using default: revenue")
            log_function_exit(logger, "extract_metric_from_query", result="metric=revenue_default")
            return "revenue"  # default
            
        except Exception as e:
            log_exception(logger, e, "extract_metric_from_query")
            log_function_exit(logger, "extract_metric_from_query", result="error")
            return "revenue"
    
    async def get_relevant_files(self, state, intent: str) -> Dict[str, Any]:
        """Get relevant files based on intent"""
        log_function_entry(logger, "get_relevant_files", intent=intent, session_id=state.get("session_id"))
        
        try:
            documents = state.get("documents", {})
            
            # Determine which file types are relevant for the intent
            relevant_types = []
            if intent in ["extract_table_data", "statistical_analysis", "financial_trend_analysis"]:
                relevant_types = ["csv", "excel", "xlsx", "xls"]
            elif intent == "document_summarizer":
                relevant_types = ["pdf", "docx"]
            
            logger.debug(f"Relevant file types for intent '{intent}': {relevant_types}")
            
            # Get files from MongoDB
            for file_type in relevant_types:
                type_key = f"{file_type}_ids"
                if type_key in documents and documents[type_key]:
                    # Get the first relevant file
                    file_id = documents[type_key][0]
                    file_data = await self._get_file_from_gridfs(file_id)
                    if file_data:
                        file_data_base64 = base64.b64encode(file_data).decode('utf-8') if file_data else None
                        logger.debug(f"Found relevant file: {file_type} with ID: {file_id}")
                        log_function_exit(logger, "get_relevant_files", result=f"file_found={file_type}")
                        return {"data": file_data_base64, "type": file_type}

            logger.warning(f"No relevant files found for intent: {intent}")
            log_function_exit(logger, "get_relevant_files", result="no_files_found")
            return None
            
        except Exception as e:
            log_exception(logger, e, f"get_relevant_files - intent: {intent}")
            log_function_exit(logger, "get_relevant_files", result="error")
            return None
    
    async def get_multiple_documents(self, state) -> List[Dict[str, Any]]:
        """Get multiple documents for comparative analysis"""
        log_function_entry(logger, "get_multiple_documents", session_id=state.get("session_id"))
        
        try:
            documents = state.get("documents", {})
            doc_list = []
            
            relevant_types = ["pdf", "docx"]
            
            for file_type in relevant_types:
                type_key = f"{file_type}_ids"
                if type_key in documents:
                    for file_id in documents[type_key]:
                        file_data = await self._get_file_from_gridfs(file_id)
                        if file_data:
                            doc_list.append({
                                "file_data": file_data,
                                "file_type": file_type,
                                "document_name": f"Document_{len(doc_list) + 1}"
                            })
            
            logger.debug(f"Retrieved {len(doc_list)} documents for comparative analysis")
            log_function_exit(logger, "get_multiple_documents", result=f"documents_count={len(doc_list)}")
            return doc_list
            
        except Exception as e:
            log_exception(logger, e, f"get_multiple_documents - session_id: {state.get('session_id')}")
            log_function_exit(logger, "get_multiple_documents", result="error")
            return []
    
    async def _get_file_from_gridfs(self, file_id: str) -> bytes:
        """Retrieve file data from GridFS"""
        log_function_entry(logger, "_get_file_from_gridfs", file_id=file_id)
        
        try:
            grid_out = await db_manager.fs_bucket.open_download_stream(ObjectId(file_id))
            file_data = await grid_out.read()
            logger.debug(f"Retrieved file data for file_id: {file_id}")
            log_function_exit(logger, "_get_file_from_gridfs", result="file_retrieved")
            return file_data
        except Exception as e:
            log_exception(logger, e, f"_get_file_from_gridfs - file_id: {file_id}")
            log_function_exit(logger, "_get_file_from_gridfs", result="error")
            return None
    
    async def get_user_links(self, session_id: str, user_id: str) -> List[Dict[str, str]]:
        """Get user's uploaded links"""
        log_function_entry(logger, "get_user_links", session_id=session_id, user_id=user_id)
        
        try:
            links_collection = db_manager.database.links
            cursor = links_collection.find({"session_id": session_id, "user_id": user_id})
            links = await cursor.to_list(length=10)
            logger.debug(f"Retrieved {len(links)} links for user: {user_id}")
            log_function_exit(logger, "get_user_links", result=f"links_count={len(links)}")
            return links
        except Exception as e:
            log_exception(logger, e, f"get_user_links - session_id: {session_id}, user_id: {user_id}")
            log_function_exit(logger, "get_user_links", result="error")
            return []
    
    def extract_urls_from_query(self, query: str) -> List[str]:
        """Extract URLs from user query"""
        log_function_entry(logger, "extract_urls_from_query", query_length=len(query))
        
        try:
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            urls = re.findall(url_pattern, query)
            logger.debug(f"Extracted {len(urls)} URLs from query")
            log_function_exit(logger, "extract_urls_from_query", result=f"urls_count={len(urls)}")
            return urls
        except Exception as e:
            log_exception(logger, e, "extract_urls_from_query")
            log_function_exit(logger, "extract_urls_from_query", result="error")
            return []
    
    def get_conversation_context(self, messages: List) -> str:
        """Get conversation context from recent messages"""
        log_function_entry(logger, "get_conversation_context", messages_count=len(messages))
        
        try:
            recent_messages = messages[-5:]  # Last 5 messages
            context = ""
            for msg in recent_messages:
                if hasattr(msg, 'content'):
                    role = "User" if isinstance(msg, HumanMessage) else "Assistant"
                    context += f"{role}: {msg.content[:200]}...\n"
            
            logger.debug(f"Generated conversation context from {len(recent_messages)} messages")
            log_function_exit(logger, "get_conversation_context", result="context_generated")
            return context
        except Exception as e:
            log_exception(logger, e, "get_conversation_context")
            log_function_exit(logger, "get_conversation_context", result="error")
            return ""
    
    def format_conversation_history(self, messages: List) -> str:
        """Format conversation history for LLM"""
        log_function_entry(logger, "format_conversation_history", messages_count=len(messages))
        
        try:
            history = ""
            for msg in messages:
                if hasattr(msg, 'content'):
                    role = "User" if isinstance(msg, HumanMessage) else "Assistant"
                    history += f"{role}: {msg.content[:100]}...\n"
            
            logger.debug(f"Formatted conversation history from {len(messages)} messages")
            log_function_exit(logger, "format_conversation_history", result="history_formatted")
            return history
        except Exception as e:
            log_exception(logger, e, "format_conversation_history")
            log_function_exit(logger, "format_conversation_history", result="error")
            return ""
        
    
    async def get_or_detect_user_language(self, session_id: str, user_id: str, user_query: str) -> str:
        """Get user language preference from DB or detect using LLM"""
        log_function_entry(logger, "get_or_detect_user_language", session_id=session_id, user_id=user_id)
        
        try:        
            # First check if user has language preference stored
            language_preference = await db_manager.database.LanguagePreference.find_one(
                {"user_id": user_id, "session_id": session_id}
            )
            
            if language_preference and language_preference.get("language"):
                detected_language = language_preference["language"]
                logger.debug(f"Found existing language preference: {detected_language} for user: {user_id}")
                log_function_exit(logger, "get_or_detect_user_language", result=f"cached_language={detected_language}")
                return detected_language
            
            # If not found, detect language using LLM
            logger.info(f"No language preference found, detecting language for user: {user_id}")
            detected_language = await detect_language_llm(user_query)
            
            # Store the detected language in database
            await self.store_user_language_preference(session_id, user_id, detected_language)
            
            logger.info(f"Language detected and stored: {detected_language} for user: {user_id}")
            log_function_exit(logger, "get_or_detect_user_language", result=f"detected_language={detected_language}")
            return detected_language
            
        except Exception as e:
            log_exception(logger, e, f"get_or_detect_user_language - session_id: {session_id}, user_id: {user_id}")
            log_function_exit(logger, "get_or_detect_user_language", result="error_fallback_english")
            return "English"
    
    async def store_user_language_preference(self, session_id: str, user_id: str, language: str):
        """Store user language preference in database"""
        log_function_entry(logger, "store_user_language_preference", session_id=session_id, user_id=user_id, language=language)
        
        try:
            language_data = {
                "user_id": user_id,
                "session_id": session_id,
                "selected_language": language,
            }
            
            # Use upsert to update existing record or create new one
            await db_manager.database.LanguagePreference.update_one(
                {"user_id": user_id, "session_id": session_id},
                {"$set": language_data},
                upsert=True
            )
            
            logger.info(f"Language preference stored: {language} for user: {user_id}")
            log_function_exit(logger, "store_user_language_preference", result="success")
            
        except Exception as e:
            log_exception(logger, e, f"store_user_language_preference - session_id: {session_id}, user_id: {user_id}, language: {language}")
            log_function_exit(logger, "store_user_language_preference", result="error")
            # Don't raise exception as this is not critical for the main flow
