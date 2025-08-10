import base64
from typing import Dict, Any
from .tool_orchestrator_utils import ToolOrchestratorUtils
from logger import setup_logger, log_exception, log_function_entry, log_function_exit

logger = setup_logger(__name__)

class ToolsUtils:
    """Utility class for tool execution logic"""
    
    def __init__(self):
        log_function_entry(logger, "__init__")
        self.utils = ToolOrchestratorUtils()
        logger.info("ToolsUtils initialized successfully")
        log_function_exit(logger, "__init__", result="initialization_successful")
    
    async def execute_tool_by_intent(
        self, 
        intent: str, 
        query: str, 
        message_id: str, 
        state, 
        mcp_server
    ) -> Dict[str, Any]:
        """Execute the appropriate tool based on intent"""
        log_function_entry(logger, "execute_tool_by_intent", intent=intent, query_length=len(query))
        
        try:
            tool_result = {"success": False, "error": "No tool executed"}

            # Direct tool mapping based on intent
            INTENT_TO_TOOL_MAPPING = {
                "statistical_analysis": "statistical_analysis",
                "financial_trend_analysis": "financial_trend_analysis", 
                "extract_table_data": "extract_table_data",
                "document_summarizer": "document_summarizer",
                "web_research": "web_research",
                "comparative_analysis": "comparative_analysis",
                "general_query": "general_query"
            }

            # Get the actual tool name
            tool_name = INTENT_TO_TOOL_MAPPING.get(intent, intent)
            logger.info(f"Tool mapping: {intent} -> {tool_name}")
            
            if tool_name in ["statistical_analysis", "financial_trend_analysis", "extract_table_data"]:
                tool_result = await self._execute_data_analysis_tool(
                    tool_name, query, message_id, state, mcp_server
                )
            elif tool_name == "document_summarizer":
                tool_result = await self._execute_document_summarizer(
                    tool_name, state, mcp_server
                )
            elif tool_name == "web_research":
                tool_result = await self._execute_web_research(
                    tool_name, query, state, mcp_server
                )
            elif tool_name == "comparative_analysis":
                tool_result = await self._execute_comparative_analysis(
                    tool_name, message_id, state, mcp_server
                )
            else:
                # Default execution with query and context for general_query
                tool_result = await self._execute_general_query(
                    tool_name, query, state, mcp_server
                )

            logger.info(f"Tool execution completed: {tool_name}, success: {tool_result.get('success', False)}")
            log_function_exit(logger, "execute_tool_by_intent", result=f"tool={tool_name}, success={tool_result.get('success', False)}")
            return tool_result

        except Exception as e:
            log_exception(logger, e, f"execute_tool_by_intent - intent: {intent}")
            tool_result = {"success": False, "error": f"Tool execution failed: {str(e)}"}
            log_function_exit(logger, "execute_tool_by_intent", result="error")
            return tool_result
    
    async def _execute_data_analysis_tool(
        self, 
        tool_name: str, 
        query: str, 
        message_id: str, 
        state, 
        mcp_server
    ) -> Dict[str, Any]:
        """Execute data analysis tools (statistical_analysis, financial_trend_analysis, extract_table_data)"""
        log_function_entry(logger, "_execute_data_analysis_tool", tool_name=tool_name)
        
        try:
            file_data = await self.utils.get_relevant_files(state, tool_name)
            if file_data:
                logger.debug(f"Found relevant file data for {tool_name}")
                
                if tool_name == "financial_trend_analysis":
                    tool_result = await mcp_server.execute_tool(
                        tool_name,
                        message_id=message_id,
                        file_data=file_data["data"], 
                        file_type=file_data["type"],
                        metric=self.utils.extract_metric_from_query(query)
                    )
                elif tool_name == "statistical_analysis":
                    tool_result = await mcp_server.execute_tool(
                        tool_name,
                        file_data=file_data["data"], 
                        file_type=file_data["type"],
                        columns=[]  # Let it analyze all numeric columns by default
                    )
                elif tool_name == "extract_table_data":
                    # Parse parameters dynamically from user query
                    extraction_params = self.utils.parse_table_extraction_params(query)
                    
                    tool_result = await mcp_server.execute_tool(
                        tool_name,
                        file_data=file_data["data"],
                        file_type=file_data["type"],
                        **extraction_params  # Unpack all parsed parameters
                    )
                else:
                    tool_result = {"success": False, "error": f"Unknown data analysis tool: {tool_name}"}
            else:
                error_msg = f"No relevant files found for {tool_name.replace('_', ' ')}"
                logger.warning(error_msg)
                tool_result = {"success": False, "error": error_msg}
            
            log_function_exit(logger, "_execute_data_analysis_tool", result=f"success={tool_result.get('success', False)}")
            return tool_result
            
        except Exception as e:
            log_exception(logger, e, f"_execute_data_analysis_tool - tool: {tool_name}")
            log_function_exit(logger, "_execute_data_analysis_tool", result="error")
            return {"success": False, "error": f"Data analysis tool execution failed: {str(e)}"}
    
    async def _execute_document_summarizer(
        self, 
        tool_name: str, 
        state, 
        mcp_server
    ) -> Dict[str, Any]:
        """Execute document summarizer tool"""
        log_function_entry(logger, "_execute_document_summarizer")
        
        try:
            file_data = await self.utils.get_relevant_files(state, "document_summarizer")
            if file_data:
                tool_result = await mcp_server.execute_tool(
                    tool_name,
                    file_data=file_data["data"], 
                    file_type=file_data["type"]
                )
            else:
                error_msg = "No PDF or DOCX files found for summarization"
                logger.warning(error_msg)
                tool_result = {"success": False, "error": error_msg}
            
            log_function_exit(logger, "_execute_document_summarizer", result=f"success={tool_result.get('success', False)}")
            return tool_result
            
        except Exception as e:
            log_exception(logger, e, "_execute_document_summarizer")
            log_function_exit(logger, "_execute_document_summarizer", result="error")
            return {"success": False, "error": f"Document summarizer execution failed: {str(e)}"}
    
    async def _execute_web_research(
        self, 
        tool_name: str, 
        query: str, 
        state, 
        mcp_server
    ) -> Dict[str, Any]:
        """Execute web research tool"""
        log_function_entry(logger, "_execute_web_research")
        
        try:
            urls = self.utils.extract_urls_from_query(query)
            if urls:
                logger.debug(f"Found URLs in query: {urls}")
                tool_result = await mcp_server.execute_tool(
                    tool_name, 
                    url=urls[0], 
                    query=query
                )
            else:
                links = await self.utils.get_user_links(state["session_id"], state["user_id"])
                if links:
                    logger.debug(f"Using user links: {links[0]['url']}")
                    tool_result = await mcp_server.execute_tool(
                        tool_name, 
                        url=links[0]["url"], 
                        query=query
                    )
                else:
                    error_msg = "No URL provided for web research"
                    logger.warning(error_msg)
                    tool_result = {"success": False, "error": error_msg}
            
            log_function_exit(logger, "_execute_web_research", result=f"success={tool_result.get('success', False)}")
            return tool_result
            
        except Exception as e:
            log_exception(logger, e, "_execute_web_research")
            log_function_exit(logger, "_execute_web_research", result="error")
            return {"success": False, "error": f"Web research execution failed: {str(e)}"}
    
    async def _execute_comparative_analysis(
        self, 
        tool_name: str, 
        message_id: str, 
        state, 
        mcp_server
    ) -> Dict[str, Any]:
        """Execute comparative analysis tool"""
        log_function_entry(logger, "_execute_comparative_analysis")
        
        try:
            documents = await self.utils.get_multiple_documents(state)
            if documents and len(documents) >= 2:
                logger.debug(f"Found {len(documents)} documents for comparative analysis")
                
                # Convert documents to the new format expected by the tool
                formatted_documents = []
                for doc in documents:
                    file_data_bytes = doc.get('file_data')
                    file_data_base64 = base64.b64encode(file_data_bytes).decode('utf-8') if file_data_bytes else None
       
                    formatted_doc = {
                        'document_type': doc.get('file_type'),
                        'document_name': doc.get('document_name'),
                        'file_data': file_data_base64
                    }
                    formatted_documents.append(formatted_doc)
                
                tool_result = await mcp_server.execute_tool(
                    tool_name,
                    message_id=message_id,
                    documents=formatted_documents,
                    comparison_columns=[]  # Let it compare all columns by default
                )
            else:
                error_msg = "Need at least 2 documents for comparative analysis"
                logger.warning(error_msg)
                tool_result = {"success": False, "error": error_msg}
            
            log_function_exit(logger, "_execute_comparative_analysis", result=f"success={tool_result.get('success', False)}")
            return tool_result
            
        except Exception as e:
            log_exception(logger, e, "_execute_comparative_analysis")
            log_function_exit(logger, "_execute_comparative_analysis", result="error")
            return {"success": False, "error": f"Comparative analysis execution failed: {str(e)}"}
    
    async def _execute_general_query(
        self, 
        tool_name: str, 
        query: str, 
        state, 
        mcp_server
    ) -> Dict[str, Any]:
        """Execute general query tool"""
        log_function_entry(logger, "_execute_general_query")
        
        try:
            logger.debug(f"Executing default tool: {tool_name}")
            tool_result = await mcp_server.execute_tool(
                tool_name,
                query=query,
                context=self.utils.get_conversation_context(state["messages"])
            )
            
            log_function_exit(logger, "_execute_general_query", result=f"success={tool_result.get('success', False)}")
            return tool_result
            
        except Exception as e:
            log_exception(logger, e, f"_execute_general_query - tool: {tool_name}")
            log_function_exit(logger, "_execute_general_query", result="error")
            return {"success": False, "error": f"General query execution failed: {str(e)}"}
