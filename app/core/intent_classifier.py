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
            
            # Updated intent patterns to match the tool mapping
            self.intent_patterns = {
                "statistical_analysis": [
                    r"analyze.*csv", r"analyze.*excel", r"data.*analysis", 
                    r"statistical.*analysis", r"average.*monthly", r"correlation",
                    r"standard.*deviation", r"statistical.*summary", r"descriptive.*statistics",
                    r"mean.*median", r"analyze.*data", r"csv.*analysis"
                ],
                "financial_trend_analysis": [
                    r"trend.*analysis", r"show.*trend", r"trend.*over.*time",
                    r"growth.*pattern", r"trend.*comparison", r"revenue.*trend", 
                    r"profit.*analysis", r"financial.*trend", r"quarterly.*trend",
                    r"sales.*trend", r"trend.*in.*data"
                ],
                "extract_table_data": [
                    r"extract.*table", r"get.*data.*table", r"table.*information",
                    r"top.*products", r"extract.*from.*table", r"table.*data",
                    r"get.*top.*records", r"filter.*data", r"search.*in.*table"
                ],
                "document_summarizer": [
                    r"summarize.*document", r"summary.*pdf", r"key.*points",
                    r"summarize.*docx", r"overview.*document", r"document.*summary",
                    r"summarize.*file", r"main.*points"
                ],
                "web_research": [
                    r"latest.*news", r"current.*market", r"web.*research",
                    r"online.*report", r"market.*trends.*online", r"search.*web",
                    r"web.*query", r"url.*analysis", r"website.*content"
                ],
                "comparative_analysis": [
                    r"compare.*documents", r"comparative.*analysis", r"comparison.*between",
                    r"compare.*files", r"difference.*between", r"contrast.*documents",
                    r"compare.*reports", r"side.*by.*side", r"vs", r"versus"
                ],
                "general_query": [
                    r"what.*is", r"how.*to", r"explain", r"tell.*me.*about",
                    r"last.*question", r"previous.*conversation", r"help.*me",
                    r"can.*you", r"hello", r"hi", r"thanks", r"thank.*you"
                ]
            }
            
            logger.info("IntentClassifier initialized successfully")
            log_function_exit(logger, "__init__", result="initialization_successful")
            
        except Exception as e:
            log_exception(logger, e, "IntentClassifier initialization")
            log_function_exit(logger, "__init__", result="initialization_failed")
            raise
    
    async def classify_intent(self, query: str) -> str:
        """Classify user intent based on query"""
        log_function_entry(logger, "classify_intent", query_length=len(query))
        
        try:
            query_lower = query.lower()
            
            # Rule-based classification first
            for intent, patterns in self.intent_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, query_lower):
                        logger.debug(f"Intent classified via rule-based: {intent}")
                        log_function_exit(logger, "classify_intent", result=f"rule_based_{intent}")
                        return intent
            
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
            
            Query: "{query}"
            
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
