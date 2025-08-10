from langchain_google_genai import ChatGoogleGenerativeAI
import os
from config.settings import settings

async def detect_language_llm(user_query: str) -> str:
    """
    Detects the language of user query using Google Generative AI and checks if it's supported.
    
    Args:
        user_query (str): The user's input query
        supported_languages (List[str]): List of supported languages
    
    Returns:
        str: Either the detected language (as it appears in supported_languages list) 
             or "language is not support" if not supported
    """

    os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY
    
    # Initialize the ChatGoogleGenerativeAI model
    llm = ChatGoogleGenerativeAI(
        model=settings.GOOGLE_GEMINI_MODEL,
        temperature=0,  # Low temperature for consistent results
        convert_system_message_to_human=True
    )
    
    # Create the supported languages string for the prompt
    supported_langs_str = ", ".join(settings.SUPPORTED_LANGUAGES)
    
    # Create the prompt for language detection
    prompt = f"""You are a language detection system. Your task is to:

1. Detect the language of the given text
2. Check if the detected language is in the supported languages list
3. Respond with ONLY the exact language name as it appears in the supported list, or "language is not support" if not found

Supported languages: {supported_langs_str}

Text to analyze: "{user_query}"

Rules:
- If the detected language matches ANY language in the supported list (case-insensitive), return the EXACT format from the supported list
- If the detected language is not in the supported list, return exactly: "language is not support"
- Return only the language name or the error message, nothing else"""

    try:
        # Get response from the LLM
        response = llm.invoke(prompt)
        result = response.content.strip()
        
        # Double-check if the result is in supported languages (case-insensitive)
        for lang in settings.SUPPORTED_LANGUAGES:
            if result.lower() == lang.lower():
                return lang

        # If result is not in supported languages
        if result != "language is not support":
            return "language is not support"

        return result
        
    except Exception as e:
        return f"Error: {str(e)}"


# # Example usage and test function
# def test_language_detection():
#     """Test function to demonstrate the language detection functionality"""
    
#     # Test cases
#     test_cases = [
#         "Hello, how are you today?",  # English
#         "¿Cómo estás hoy?",  # Spanish
#         "Bonjour, comment allez-vous?",  # French
#         "Guten Tag, wie geht es Ihnen?",  # German
#         "こんにちは、元気ですか？",  # Japanese
#         "नमस्ते, आप कैसे हैं?",  # Hindi
#         "Здравствуйте, как дела?",  # Russian
#         "Привіт, як справи?",  # Ukrainian (not in supported list)
#         "Merhaba, nasılsınız?",  # Turkish (not in supported list)
#     ]
    
#     print("Language Detection Test Results:")
#     print("=" * 50)
    
#     for i, query in enumerate(test_cases, 1):
#         print(f"\nTest {i}:")
#         print(f"Query: {query}")
        
#         # Note: You need to set your Google API key before running this
#         result = detect_language_llm(query)
#         print(f"Result: {result}")
        