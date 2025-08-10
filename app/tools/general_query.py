from .base_tool import BaseMCPTool
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from logger import setup_logger, log_exception, log_function_entry, log_function_exit

logger = setup_logger(__name__)

class GeneralQuery(BaseMCPTool):
    def __init__(self):
        log_function_entry(logger, "__init__")
        try:
            super().__init__(
                name="general_query",
                description="Handles general financial queries and conversations with financial context validation"
            )
            
            # Initialize LLM for query processing
            self.llm = ChatGoogleGenerativeAI(
                model=settings.GOOGLE_GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.3
            )
            logger.info("GeneralQuery tool initialized successfully")
            log_function_exit(logger, "__init__", result="initialization_successful")
        except Exception as e:
            log_exception(logger, e, "GeneralQuery initialization")
            log_function_exit(logger, "__init__", result="initialization_failed")
            raise
    
    async def execute(self, query: str, context: str = None) -> Dict[str, Any]:
        log_function_entry(logger, "execute", query_length=len(query), has_context=context is not None)
        
        try:
            # Process query directly with LLM
            response = await self._process_query_with_llm(query, context)
            
            result = {
                "success": True,
                "response": response
            }
            
            logger.info("General query executed successfully")
            log_function_exit(logger, "execute", result="success")
            return result
            
        except Exception as e:
            log_exception(logger, e, f"execute - query: {query[:100]}...")
            log_function_exit(logger, "execute", result="error")
            return {
                "success": False,
                "error": f"General query processing failed: {str(e)}"
            }
    
    async def _process_query_with_llm(self, query: str, context: str = None) -> str:
        """Process query with LLM - respond to financial queries or redirect non-financial ones"""
        log_function_entry(logger, "_process_query_with_llm", query_length=len(query), has_context=context is not None)
        
        try:
            context_str = f"\nContext: {context}" if context else ""
            
            prompt = f"""
            You are a financial intelligence assistant. Analyze the user's query and respond appropriately:

            If the query is related to finance, business, economics, investing, money management, or any financial topic:
            - Provide a helpful, accurate answer
            - Keep your response short and simple (maximum 50 words)
            - Be direct and informative

            If the query is NOT related to financial topics:
            - Respond exactly with: "I am a financial chatbot, please ask questions related to financial."

            User Query: {query}{context_str}

            Response:
            """
            
            response = await self.llm.ainvoke(prompt)
            result = response.content.strip()
            
            logger.debug(f"LLM response generated for query: {query[:50]}...")
            log_function_exit(logger, "_process_query_with_llm", result="response_generated")
            return result
            
        except Exception as e:
            log_exception(logger, e, f"_process_query_with_llm - query: {query[:100]}...")
            log_function_exit(logger, "_process_query_with_llm", result="error")
            return "I apologize, but I encountered an error while processing your query. Please try again."
    
    def get_schema(self) -> Dict[str, Any]:
        log_function_entry(logger, "get_schema")
        try:
            schema = {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string", 
                            "description": "User query to be processed"
                        },
                        "context": {
                            "type": "string", 
                            "description": "Additional context from conversation history"
                        }
                    },
                    "required": ["query"]
                }
            }
            log_function_exit(logger, "get_schema", result="schema_returned")
            return schema
        except Exception as e:
            log_exception(logger, e, "get_schema")
            log_function_exit(logger, "get_schema", result="error")
            return {}