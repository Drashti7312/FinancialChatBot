from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages
from config.settings import settings
from mcp.mcp_server import mcp_server
from core.intent_classifier import intent_classifier
from logger import setup_logger, log_exception, log_function_entry, log_function_exit
from .tool_orchestrator_utils import ToolOrchestratorUtils
from .tools_utils import ToolsUtils

logger = setup_logger(__name__)

class OrchestratorState(TypedDict):
    messages: Annotated[List, add_messages]
    session_id: str
    user_id: str
    message_id: str
    user_query_language: Optional[str] = "English"
    intent: str
    tool_result: Dict[str, Any]
    documents: Dict[str, List[str]]

class ToolOrchestrator:
    def __init__(self):
        log_function_entry(logger, "__init__")
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=settings.GOOGLE_GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.3
            )
            self.mcp_server = mcp_server
            self.intent_classifier = intent_classifier
            self.utils = ToolOrchestratorUtils()
            self.tools_utils = ToolsUtils()
            
            # Build the orchestration graph
            self.graph = self._build_graph()
            logger.info("ToolOrchestrator initialized successfully")
            log_function_exit(logger, "__init__", result="initialization_successful")
        except Exception as e:
            log_exception(logger, e, "ToolOrchestrator initialization")
            log_function_exit(logger, "__init__", result="initialization_failed")
            raise
    
    def _build_graph(self):
        """Build the LangGraph orchestration graph"""
        log_function_entry(logger, "_build_graph")
        try:
            builder = StateGraph(OrchestratorState)
            
            # Add nodes
            builder.add_node("detect_user_language", self._detect_user_language)
            builder.add_node("classify_intent", self._classify_intent_node)
            builder.add_node("execute_tool", self._execute_tool_node)
            builder.add_node("generate_response", self._generate_response_node)
            
            # Add edges
            builder.add_edge(START, "detect_user_language")
            builder.add_edge("detect_user_language", "classify_intent")
            builder.add_edge("classify_intent", "execute_tool")
            builder.add_edge("execute_tool", "generate_response")
            builder.add_edge("generate_response", END)
            
            graph = builder.compile()
            logger.debug("Orchestration graph built successfully")
            log_function_exit(logger, "_build_graph", result="graph_compiled")
            return graph
        except Exception as e:
            log_exception(logger, e, "_build_graph")
            log_function_exit(logger, "_build_graph", result="error")
            raise

    async def _detect_user_language(self, state: OrchestratorState) -> Dict[str, Any]:
        '''Fetch or Detect User Language'''
        print("calling, please 11111111111111111111111111111")
        log_function_entry(logger, "_detect_user_language", session_id=state.get("session_id"), user_id=state.get("user_id"))
        
        # Add debug log to confirm function is being called
        logger.info(f"_detect_user_language called for session: {state.get('session_id')}, user: {state.get('user_id')}")
        
        try:
            session_id = state.get("session_id")
            user_id = state.get("user_id")
            last_message = state["messages"][-1]
            user_query = last_message.content if hasattr(last_message, 'content') else str(last_message)
            print("2222222222222222222222222222222222")
            logger.debug(f"Detecting language for query: {user_query[:100]}...")
            
            # Call utility function to get or detect language
            detected_language = await self.utils.get_or_detect_user_language(
                session_id=session_id,
                user_id=user_id,
                user_query=user_query
            )
            print("detected language 333333333333333333333", detected_language)
            logger.info(f"Language detected/retrieved: {detected_language} for user: {user_id}")
            log_function_exit(logger, "_detect_user_language", result=f"language={detected_language}")
            return {"user_query_language": detected_language}
            
        except Exception as e:
            log_exception(logger, e, f"_detect_user_language - session_id: {state.get('session_id')}, user_id: {state.get('user_id')}")
            log_function_exit(logger, "_detect_user_language", result="error")
            return {"user_query_language": "English"}
    
    async def _classify_intent_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """Classify user intent"""
        log_function_entry(logger, "_classify_intent_node", session_id=state.get("session_id"), user_id=state.get("user_id"))
        
        # Add debug log to confirm function is being called
        logger.info(f"_classify_intent_node called for session: {state.get('session_id')}")
        
        try:
            last_message = state["messages"][-1]
            query = last_message.content if hasattr(last_message, 'content') else str(last_message)
            
            intent = await self.intent_classifier.classify_intent(query)
            logger.debug(f"Intent classified: {intent} for query: {query[:100]}...")
            
            log_function_exit(logger, "_classify_intent_node", result=f"intent={intent}")
            return {"intent": intent}
        except Exception as e:
            log_exception(logger, e, f"_classify_intent_node - session_id: {state.get('session_id')}, user_id: {state.get('user_id')}")
            log_function_exit(logger, "_classify_intent_node", result="error")
            return {"intent": "general_query"}
    
    async def _execute_tool_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """Execute the appropriate tool based on intent"""
        log_function_entry(logger, "_execute_tool_node", session_id=state.get("session_id"), user_id=state.get("user_id"), intent=state.get("intent"))
        print(state, 4444444444444444444444444444444444444444444)
        # Add debug log to confirm function is being called
        logger.info(f"_execute_tool_node called for session: {state.get('session_id')}, intent: {state.get('intent')}")
        
        try:
            intent = state["intent"]
            last_message = state["messages"][-1]
            query = last_message.content if hasattr(last_message, 'content') else str(last_message)
            message_id = state["message_id"]
            logger.debug(f"Executing tool for intent: {intent}, query: {query[:100]}...")
            
            # Use tools_utils to execute the appropriate tool
            tool_result = await self.tools_utils.execute_tool_by_intent(
                intent=intent,
                query=query,
                message_id=message_id,
                state=state,
                mcp_server=self.mcp_server
            )

            logger.info(f"Tool execution completed: {intent}, success: {tool_result.get('success', False)}")
            log_function_exit(logger, "_execute_tool_node", result=f"intent={intent}, success={tool_result.get('success', False)}")
            return {"tool_result": tool_result}

        except Exception as e:
            log_exception(logger, e, f"_execute_tool_node - intent: {state.get('intent')}, session_id: {state.get('session_id')}")
            tool_result = {"success": False, "error": f"Tool execution failed: {str(e)}"}
            log_function_exit(logger, "_execute_tool_node", result="error")
            return {"tool_result": tool_result}

    async def _generate_response_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """Generate final response using ResponseProcessor for formatting and translation"""
        log_function_entry(logger, "_generate_response_node", session_id=state.get("session_id"), user_id=state.get("user_id"))
        
        # Add debug log to confirm function is being called
        logger.info(f"_generate_response_node called for session: {state.get('session_id')}")
        
        try:
            tool_result = state["tool_result"]
            last_message = state["messages"][-1]
            query = last_message.content if hasattr(last_message, 'content') else str(last_message)
            response_language = state.get("responce_language", "English")  # Fixed typo in key name
            intent = state.get("intent", "general_query")
            
            logger.debug(f"Generating response in language: {response_language}")
            
            # Import ResponseProcessor here to avoid circular imports
            from .response_processor import ResponseProcessor
            response_processor = ResponseProcessor(self.llm)
            
            # Handle successful tool execution
            if tool_result.get("success", False):
                logger.info("Processing successful tool result")
                
                response_content = await response_processor.process_and_format_response(
                    tool_result=tool_result,
                    intent=intent,
                    user_query=query,
                    response_language=response_language
                )
                
                ai_message = AIMessage(content=response_content)
                logger.debug("Generated response from successful tool execution")
                
            else:
                # Handle tool failure cases
                logger.info("Processing failed tool result")
                
                response_content = await response_processor.handle_tool_failure(
                    tool_result=tool_result,
                    user_query=query,
                    intent=intent,
                    response_language=response_language
                )
                
                ai_message = AIMessage(content=response_content)
                logger.debug("Generated response for tool failure")
            
            log_function_exit(logger, "_generate_response_node", result="response_generated")
            return {"messages": [ai_message]}
            
        except Exception as e:
            log_exception(logger, e, f"_generate_response_node - session_id: {state.get('session_id')}, user_id: {state.get('user_id')}")
            log_function_exit(logger, "_generate_response_node", result="error")
            
            # Fallback error response
            response_language = state.get("responce_language", "English")
            error_message_content = "I apologize, but I encountered an error while processing your request."
            
            # Try to translate error message if needed
            if response_language != "English":
                try:
                    from .response_processor import ResponseProcessor
                    response_processor = ResponseProcessor(self.llm)
                    error_message_content = await response_processor._translate_simple_text(
                        error_message_content, 
                        response_language
                    )
                except Exception as translate_error:
                    log_exception(logger, translate_error, "Error message translation failed")
                    # Keep English error message as final fallback
            
            error_message = AIMessage(content=error_message_content)
            return {"messages": [error_message]}

    async def process_query(
            self, 
            session_id: str, 
            user_id: str, 
            query: str, 
            message_id: str,
            documents: Dict[str, List[str]] = None,
    ) -> str:
        """Main method to process user query"""
        log_function_entry(logger, "process_query", session_id=session_id, user_id=user_id, message_id=message_id, query_length=len(query))
        
        # Add debug log to confirm process_query is being called
        logger.info(f"process_query started for session: {session_id}, user: {user_id}, query: {query[:100]}...")
        
        try:
            initial_state = OrchestratorState(
                messages=[HumanMessage(content=query)],
                session_id=session_id,
                user_id=user_id,
                message_id=message_id,
                intent="",
                tool_result={},
                documents=documents or {}
            )
            
            logger.info(f"Processing query for session: {session_id}, user: {user_id}")
            logger.debug(f"Initial state: {initial_state}")
            
            # Execute the graph
            logger.info("Starting graph execution...")
            result = await self.graph.ainvoke(initial_state)
            logger.info("Graph execution completed")
            logger.debug(f"Graph result keys: {result.keys()}")
            
            # Return the final AI message
            ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
            if ai_messages:
                response = ai_messages[-1].content
                logger.info(f"Query processed successfully for session: {session_id}")
                log_function_exit(logger, "process_query", result="response_generated")
                return response
            else:
                error_msg = "I apologize, but I couldn't process your request properly."
                logger.warning(f"No AI response generated for session: {session_id}")
                log_function_exit(logger, "process_query", result="no_response")
                return error_msg
                
        except Exception as e:
            log_exception(logger, e, f"process_query - session_id: {session_id}, user_id: {user_id}")
            log_function_exit(logger, "process_query", result="error")
            return "I apologize, but I encountered an error while processing your request."

# Create global orchestrator
orchestrator = ToolOrchestrator()
