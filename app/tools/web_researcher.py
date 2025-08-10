import requests
from abc import ABC, abstractmethod
from typing import Any, Dict
from bs4 import BeautifulSoup
from langchain_google_genai import ChatGoogleGenerativeAI
from urllib.parse import urlparse
import re
from config.settings import settings
from .base_tool import BaseMCPTool
from logger import setup_logger, log_exception, log_function_entry, log_function_exit

logger = setup_logger(__name__)

class WebQueryTool(BaseMCPTool):
    def __init__(self):
        log_function_entry(logger, "__init__")
        try:
            super().__init__(
                name="web_research",
                description="Answer user questions based on web URL content using Google Generative AI"
            )
            self.llm = ChatGoogleGenerativeAI(
                model=settings.GOOGLE_GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.3
            )
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            logger.info("WebQueryTool initialized successfully")
            log_function_exit(logger, "__init__", result="initialization_successful")
        except Exception as e:
            log_exception(logger, e, "WebQueryTool initialization")
            log_function_exit(logger, "__init__", result="initialization_failed")
            raise
    
    def is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        log_function_entry(logger, "is_valid_url", url=url)
        try:
            result = urlparse(url)
            is_valid = all([result.scheme, result.netloc])
            logger.debug(f"URL validation result: {is_valid} for {url}")
            log_function_exit(logger, "is_valid_url", result=f"valid={is_valid}")
            return is_valid
        except Exception as e:
            log_exception(logger, e, f"is_valid_url - url: {url}")
            log_function_exit(logger, "is_valid_url", result="error")
            return False
    
    def fetch_web_content(self, url: str) -> str:
        """Fetch and extract text content from web URL"""
        log_function_entry(logger, "fetch_web_content", url=url)
        
        try:
            if not self.is_valid_url(url):
                raise ValueError("Invalid URL format")
            
            logger.info(f"Fetching web content from: {url}")
            
            # Fetch the webpage
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            if not text:
                raise Exception("No readable content found on the webpage")
            
            logger.info(f"Successfully fetched {len(text)} characters from {url}")
            log_function_exit(logger, "fetch_web_content", result="content_fetched")
            return text
            
        except requests.RequestException as e:
            log_exception(logger, e, f"fetch_web_content - url: {url}")
            log_function_exit(logger, "fetch_web_content", result="request_error")
            raise Exception(f"Failed to fetch URL: {str(e)}")
        except Exception as e:
            log_exception(logger, e, f"fetch_web_content - url: {url}")
            log_function_exit(logger, "fetch_web_content", result="error")
            raise Exception(f"Error processing webpage content: {str(e)}")
    
    async def answer_query(self, content: str, query: str, url: str) -> str:
        """Answer user query based on web content using LLM"""
        log_function_entry(logger, "answer_query", query_length=len(query), content_length=len(content), url=url)
        
        try:
            prompt = f"""
You are an intelligent assistant that answers questions based on web content. You have been provided with the content from a webpage and a user's query about that content.

Your task is to:
1. Analyze the provided web content thoroughly
2. Answer the user's question accurately and comprehensively
3. Base your answer ONLY on the information available in the provided content
4. If the content doesn't contain enough information to answer the question, clearly state that
5. Provide specific details and quotes when relevant
6. Structure your answer in a clear, organized manner
Answer should in 

Web Content Source: {url}

Web Content:
{content}

User Query: {query}

Instructions:
- Be precise and factual in your response
- If you find relevant information, provide a detailed answer with specific examples
- If the information is incomplete, mention what aspects cannot be answered from the content
- Use clear headings or bullet points when appropriate for better readability
- Maintain a professional and helpful tone

Summarize in 500 words
"""
            
            response = await self.llm.ainvoke(prompt)
            result = response.content.strip()
            
            logger.info(f"Generated answer for query: {query[:50]}...")
            log_function_exit(logger, "answer_query", result="answer_generated")
            return result
            
        except Exception as e:
            log_exception(logger, e, f"answer_query - query: {query[:100]}...")
            log_function_exit(logger, "answer_query", result="error")
            return f"Error processing query: {str(e)}"
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the web query tool"""
        log_function_entry(logger, "execute", url=kwargs.get("url", ""), query=kwargs.get("query", ""))
        try:
            # Get parameters
            url = kwargs.get("url", "").strip()
            query = kwargs.get("query", "").strip()
            
            if not url:
                log_function_exit(logger, "execute", result="no_url_provided")
                return {
                    "success": False,
                    "error": "No URL provided"
                }
            
            if not query:
                log_function_exit(logger, "execute", result="no_query_provided")
                return {
                    "success": False,
                    "error": "No query provided"
                }
            
            # Fetch web content
            web_content = self.fetch_web_content(url)
            
            # Truncate content if too long (to avoid token limits)
            max_content_length = 4000  # Adjust based on your model's context window
            if len(web_content) > max_content_length:
                web_content = web_content[:max_content_length] + "...\n[Content truncated due to length]"
            
            # Generate answer
            answer = await self.answer_query(web_content, query, url)
            
            log_function_exit(logger, "execute", result="success")
            return {
                "success": True,
                "answer": answer,
                "url": url,
                "query": query,
                "content_length": len(web_content),
                "content_truncated": len(web_content) > max_content_length
            }
            
        except Exception as e:
            log_exception(logger, e, f"execute - url: {kwargs.get('url', '')}, query: {kwargs.get('query', '')}")
            log_function_exit(logger, "execute", result="error")
            return {
                "success": False,
                "error": str(e),
                "url": kwargs.get("url", ""),
                "query": kwargs.get("query", "")
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool schema for MCP registration"""
        log_function_entry(logger, "get_schema")
        try:
            schema = {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The web URL to fetch content from"
                        },
                        "query": {
                            "type": "string",
                            "description": "The user's question about the web content"
                        }
                    },
                    "required": ["url", "query"]
                }
            }
            log_function_exit(logger, "get_schema", result="success")
            return schema
        except Exception as e:
            log_exception(logger, e, "get_schema")
            log_function_exit(logger, "get_schema", result="error")
            raise


# Example usage
async def main():
    # Initialize the tool with your Google API key
    web_query_tool = WebQueryTool()
    
    # Example query
    result = await web_query_tool.execute(
        url="https://en.wikipedia.org/wiki/Python_(programming_language)",
        query="What are the main features of Python programming language?"
    )
    
    if result["success"]:
        print("Answer:", result["answer"])
        print("Content length:", result["content_length"])
        print("URL:", result["url"])
    else:
        print("Error:", result["error"])

