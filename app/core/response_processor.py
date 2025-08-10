from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from logger import setup_logger, log_exception, log_function_entry, log_function_exit
import json

logger = setup_logger(__name__)

class ResponseProcessor:
    def __init__(self, llm: ChatGoogleGenerativeAI):
        """
        Initialize ResponseProcessor with LLM instance
        
        Args:
            llm: ChatGoogleGenerativeAI instance for processing responses
        """
        log_function_entry(logger, "__init__")
        self.llm = llm
        logger.info("ResponseProcessor initialized successfully")
        log_function_exit(logger, "__init__", result="initialization_successful")
    
    async def process_and_format_response(
        self, 
        tool_result: Dict[str, Any], 
        intent: str, 
        user_query: str,
        user_query_language: str = "English"
    ) -> str:
        """
        Main method to process tool result and format response in one LLM call
        
        Args:
            tool_result: Result from tool execution
            intent: User's intent classification
            user_query: Original user query
            user_query_language: Target language for response
            
        Returns:
            Formatted response string
        """
        log_function_entry(
            logger, 
            "process_and_format_response", 
            intent=intent, 
            language=user_query_language,
            tool_success=tool_result.get("success", False)
        )
        
        try:
            # Single LLM call to structure and translate (if needed)
            final_response = await self._structure_and_translate_response(
                tool_result=tool_result,
                intent=intent,
                user_query=user_query,
                target_language=user_query_language
            )
            
            logger.info(f"Response processed successfully in {user_query_language}")
            log_function_exit(logger, "process_and_format_response", result="success")
            return final_response
            
        except Exception as e:
            log_exception(logger, e, f"process_and_format_response - intent: {intent}, language: {user_query_language}")
            log_function_exit(logger, "process_and_format_response", result="error")
            
            # Fallback response
            fallback_msg = "I apologize, but I encountered an error while processing your request."
            if user_query_language != "English":
                try:
                    fallback_msg = await self._translate_simple_text(fallback_msg, user_query_language)
                except:
                    pass
            return fallback_msg
    
    async def _structure_and_translate_response(
        self, 
        tool_result: Dict[str, Any], 
        intent: str, 
        user_query: str,
        target_language: str
    ) -> str:
        """
        Structure tool result and translate in a single LLM call for efficiency
        
        Args:
            tool_result: Raw tool result
            intent: User's intent
            user_query: Original query
            target_language: Target language for response
            
        Returns:
            Structured and translated response string
        """
        log_function_entry(logger, "_structure_and_translate_response", intent=intent, target_language=target_language)
        
        try:
            # Convert tool_result to string for prompt
            tool_data = json.dumps(tool_result, indent=2, default=str)
            # Language instruction for the prompt
            language_instruction = ""
            if target_language != "English":
                language_instruction = f"""
                IMPORTANT: Your final response must be in {target_language}.
                - Maintain all numerical values and dates exactly as they are
                - Keep technical financial terms but provide brief explanations in parentheses if needed
                - Preserve professional tone and formatting in {target_language}
                """
            else:
                language_instruction = "Respond in English."
            
            prompt = f"""
            You are a financial intelligence assistant. Process the following tool result and create a clear, professional response for the user.
            
            User Query: {user_query}
            Intent: {intent}
            Tool Result: {tool_data}
            
            Instructions:
            1. Structure the information clearly and professionally
            2. If possible, use tables to organize complex information, else provide data in a clear format
            3. Include all relevant numbers, dates, and key details
            4. Make the response conversational but professional
            5. If the tool failed, explain what went wrong and suggest alternatives
            6. Focus on what's most important to the user
            7. Keep the response concise but complete
            8. Directly answer the user's question based on the tool result
            9. Do not add anything other than tool result, just modify tool result as needed
            
            {language_instruction}
            
            Provide your structured response:
            """
            
            response = await self.llm.ainvoke(prompt)
            final_content = response.content.strip()
            
            logger.debug(f"Tool result structured and translated successfully for intent: {intent} in {target_language}")
            log_function_exit(logger, "_structure_and_translate_response", result="success")
            return final_content
            
        except Exception as e:
            log_exception(logger, e, f"_structure_and_translate_response - intent: {intent}, language: {target_language}")
            log_function_exit(logger, "_structure_and_translate_response", result="error")
            
            # Fallback to simple formatting
            if tool_result.get("success", False):
                fallback = f"Here's what I found: {str(tool_result.get('data', tool_result))}"
            else:
                fallback = f"I encountered an issue: {tool_result.get('error', 'Unknown error occurred')}"
            
            # Quick translation attempt for fallback if needed
            if target_language != "English":
                try:
                    fallback = await self._translate_simple_text(fallback, target_language)
                except:
                    pass
            
            return fallback
    
    async def _translate_simple_text(self, text: str, target_language: str) -> str:
        """
        Simple text translation for error messages and short text
        
        Args:
            text: Text to translate
            target_language: Target language
            
        Returns:
            Translated text
        """
        log_function_entry(logger, "_translate_simple_text", target_language=target_language)
        
        try:
            prompt = f"""
            Translate this text to {target_language}:
            "{text}"
            
            Provide only the translation:
            """
            
            response = await self.llm.ainvoke(prompt)
            translated_text = response.content.strip()
            
            log_function_exit(logger, "_translate_simple_text", result="translated")
            return translated_text
            
        except Exception as e:
            log_exception(logger, e, f"_translate_simple_text - target_language: {target_language}")
            log_function_exit(logger, "_translate_simple_text", result="error")
            return text
    
    async def handle_tool_failure(
        self, 
        tool_result: Dict[str, Any], 
        user_query: str, 
        intent: str,
        user_query_language: str = "English"
    ) -> str:
        """
        Handle tool failure cases with helpful error messages and suggestions in one LLM call
        
        Args:
            tool_result: Failed tool result
            user_query: Original user query
            intent: User's intent
            user_query_language: Target language for response
            
        Returns:
            Helpful error response with suggestions
        """
        log_function_entry(logger, "handle_tool_failure", intent=intent, language=user_query_language)
        
        try:
            error_info = tool_result.get("error", "Unknown error occurred")
            
            # Language instruction
            language_instruction = ""
            if user_query_language != "English":
                language_instruction = f"Respond in {user_query_language} while maintaining professional tone."
            else:
                language_instruction = "Respond in English."
            
            prompt = f"""
            You are a Expert Financial ChatBot
            The tool execution failed for a financial query. Provide a helpful response that:
            1. Acknowledges the issue professionally
            2. Explains what might have gone wrong (in simple terms)
            3. If the issue related document suggest them to upload relevant documents 

            Answer in max in one or two line. 
            
            User Query: {user_query}
            Intent: {intent}
            Error: {error_info}
            
            {language_instruction}
            
            Create a helpful, professional response that maintains user confidence:
            """
            
            response = await self.llm.ainvoke(prompt)
            failure_response = response.content.strip()
            
            logger.info(f"Tool failure handled successfully in {user_query_language}")
            log_function_exit(logger, "handle_tool_failure", result="handled")
            return failure_response
            
        except Exception as e:
            log_exception(logger, e, f"handle_tool_failure - intent: {intent}, language: {user_query_language}")
            log_function_exit(logger, "handle_tool_failure", result="error")
            
            # Ultimate fallback
            fallback = "I apologize, but I'm currently unable to process your request. Please try again later or rephrase your question."
            if user_query_language != "English":
                try:
                    fallback = await self._translate_simple_text(fallback, user_query_language)
                except:
                    pass
            return fallback
