from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from logger import setup_logger, log_exception, log_function_entry, log_function_exit
import re

logger = setup_logger(__name__)

class IntentClassifier:
    def __init__(self):
        log_function_entry(logger, "__init__")
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=settings.GOOGLE_GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.1
            )
            
            logger.info("IntentClassifier initialized successfully")
            log_function_exit(logger, "__init__", result="initialization_successful")
            
        except Exception as e:
            log_exception(logger, e, "IntentClassifier initialization")
            log_function_exit(logger, "__init__", result="initialization_failed")
            raise
    
    async def classify_intent(self, query: str, context: list) -> str:
        """Classify user intent based on query"""
        log_function_entry(logger, "classify_intent", query_length=len(query))
        
        try: 
            # LLM-based classification as fallback
            logger.debug("Rule-based classification failed, using LLM-based classification")
            prompt = f"""
            Classify the following query into one of these financial chatbot intents:
            The user query may be in any of the languages.
                Detect the intent regardless of the language and translate internally if necessary.
            - statistical_analysis: For analyzing CSV/Excel data, calculating statistics, descriptive analysis
            - financial_trend_analysis: For analyzing trends in financial data over time, growth patterns
            - extract_table_data: For extracting specific data from tables, filtering, getting top records
            - document_summarizer: For summarizing PDF/DOCX documents, getting key points
            - web_research: For researching current market/financial information online, analyzing web content
            - comparative_analysis: For comparing multiple documents or datasets side by side
            - general_query: For general questions, greetings, and conversations
            - Refer Previous Messages if there is any kind of confusion
            If user mentioned online search or web urls or url, latest news or any kind of web research, classify as web_research not as general_query
            Query: "{query}"
            Previous Messages: "{context}"

            Return only the intent name exactly as listed above.
            """
            response = await self.llm.ainvoke(prompt)
            intent = response.content.strip().lower()
            
            # Validate the intent matches our available intents
            valid_intents = [
                "statistical_analysis", 
                "financial_trend_analysis", 
                "extract_table_data",
                "document_summarizer", 
                "web_research", 
                "comparative_analysis", 
                "general_query"
            ]
            
            if intent in valid_intents:
                logger.debug(f"Intent classified via LLM: {intent}")
                log_function_exit(logger, "classify_intent", result=f"llm_based_{intent}")
                return intent
            else:
                logger.warning(f"Invalid intent returned by LLM: {intent}, defaulting to general_query")
                log_function_exit(logger, "classify_intent", result="llm_based_general_query")
                return "general_query"
                
        except Exception as e:
            log_exception(logger, e, f"classify_intent - query: {query}")
            logger.warning("LLM classification failed, defaulting to general_query")
            log_function_exit(logger, "classify_intent", result="error_defaulting_to_general_query")
            return "general_query"

# Create global intent classifier
intent_classifier = IntentClassifier()
