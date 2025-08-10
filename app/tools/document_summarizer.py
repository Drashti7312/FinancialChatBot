import io
import base64
from .base_tool import BaseMCPTool
from typing import Any, Dict
import PyPDF2
import pdfplumber
from docx import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings
from logger import setup_logger, log_exception, log_function_entry, log_function_exit


class DocumentSummarizerTool(BaseMCPTool):
    def __init__(self):
        log_function_entry(setup_logger(__name__), "DocumentSummarizerTool.__init__")
        
        try:
            super().__init__(
                name="document_summarizer",
                description="Summarize PDF or DOCX documents using Google Generative AI"
            )
            self.llm = ChatGoogleGenerativeAI(
                model=settings.GOOGLE_GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.3
            )
            log_function_exit(setup_logger(__name__), "DocumentSummarizerTool.__init__", result="initialization_completed")
        except Exception as e:
            log_exception(setup_logger(__name__), e, "DocumentSummarizerTool.__init__")
            raise
    
    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extract text from PDF bytes with multiple fallback methods"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "extract_text_from_pdf", file_size=len(file_bytes))
        
        text = ""
        
        # Method 1: Try pdfplumber first (more robust)
        try:
            logger.debug("Attempting to extract text using pdfplumber")
            pdf_file = io.BytesIO(file_bytes)
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                logger.info("Successfully extracted text using pdfplumber")
                log_function_exit(logger, "extract_text_from_pdf", result=f"extracted_{len(text)}_characters")
                return text.strip()
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")
        
        # Method 2: Try PyPDF2 with strict=False
        try:
            logger.debug("Attempting to extract text using PyPDF2 with strict=False")
            pdf_file = io.BytesIO(file_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file, strict=False)
            text = ""
            for page in pdf_reader.pages:
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as page_error:
                    logger.debug(f"Failed to extract text from page: {page_error}")
                    continue
            if text.strip():
                logger.info("Successfully extracted text using PyPDF2 with strict=False")
                log_function_exit(logger, "extract_text_from_pdf", result=f"extracted_{len(text)}_characters")
                return text.strip()
        except Exception as e:
            logger.warning(f"PyPDF2 with strict=False failed: {e}")
        
        # Method 3: Try PyPDF2 with different approach
        try:
            logger.debug("Attempting to extract text using PyPDF2 temp file method")
            pdf_file = io.BytesIO(file_bytes)
            # Reset stream position
            pdf_file.seek(0)
            with open('temp_pdf.pdf', 'wb') as temp_file:
                temp_file.write(file_bytes)
            
            with open('temp_pdf.pdf', 'rb') as temp_file:
                pdf_reader = PyPDF2.PdfReader(temp_file)
                text = ""
                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as page_error:
                        logger.debug(f"Failed to extract text from page: {page_error}")
                        continue
            
            import os
            if os.path.exists('temp_pdf.pdf'):
                os.remove('temp_pdf.pdf')
                
            if text.strip():
                logger.info("Successfully extracted text using PyPDF2 temp file method")
                log_function_exit(logger, "extract_text_from_pdf", result=f"extracted_{len(text)}_characters")
                return text.strip()
        except Exception as e:
            logger.warning(f"PyPDF2 temp file method failed: {e}")
        
        # If all methods fail
        if not text.strip():
            error_msg = "Unable to extract text from PDF. The file may be corrupted, encrypted, or contain only images."
            logger.error(error_msg)
            log_function_exit(logger, "extract_text_from_pdf", result="extraction_failed")
            raise Exception(error_msg)
    
    def extract_text_from_docx(self, file_bytes: bytes) -> str:
        """Extract text from DOCX bytes"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "extract_text_from_docx", file_size=len(file_bytes))
        
        try:
            docx_file = io.BytesIO(file_bytes)
            doc = Document(docx_file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            result_text = text.strip()
            logger.info(f"Successfully extracted text from DOCX: {len(result_text)} characters")
            log_function_exit(logger, "extract_text_from_docx", result=f"extracted_{len(result_text)}_characters")
            return result_text
        except Exception as e:
            error_msg = f"Error extracting DOCX text: {str(e)}"
            log_exception(logger, e, "extract_text_from_docx")
            log_function_exit(logger, "extract_text_from_docx", result="extraction_failed")
            raise Exception(error_msg)
    
    def extract_text(self, file_bytes: bytes, file_type: str) -> str:
        """Extract text based on file type"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "extract_text", file_type=file_type, file_size=len(file_bytes))
        
        try:
            file_type = file_type.lower()
            
            if file_type == "pdf":
                result = self.extract_text_from_pdf(file_bytes)
            elif file_type == "docx":
                result = self.extract_text_from_docx(file_bytes)
            else:
                error_msg = f"Unsupported file type: {file_type}"
                logger.error(error_msg)
                log_function_exit(logger, "extract_text", result="unsupported_file_type")
                raise ValueError(error_msg)
            
            log_function_exit(logger, "extract_text", result=f"extracted_{len(result)}_characters")
            return result
        except Exception as e:
            log_exception(logger, e, "extract_text")
            log_function_exit(logger, "extract_text", result="extraction_failed")
            raise
    
    async def summarize_text(self, text: str) -> str:
        """Summarize text using Google Generative AI"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "summarize_text", text_length=len(text))
        
        try:
            if not text.strip():
                logger.warning("No text content found in the document")
                log_function_exit(logger, "summarize_text", result="no_text_content")
                return "No text content found in the document."
            
            prompt = f"""
            Please provide a concise summary of the following document. Focus on capturing the main insights, key points, and important findings. Keep the summary clear and well-structured.

            Document content:
            {text}

            Summary:
            """
            
            logger.debug("Generating summary using Google Generative AI")
            response = await self.llm.ainvoke(prompt)
            summary = response.content
            
            logger.info(f"Successfully generated summary: {len(summary)} characters")
            log_function_exit(logger, "summarize_text", result=f"summary_generated_{len(summary)}_characters")
            return summary
        except Exception as e:
            error_msg = f"Error generating summary: {str(e)}"
            log_exception(logger, e, "summarize_text")
            log_function_exit(logger, "summarize_text", result="summary_generation_failed")
            raise Exception(error_msg)
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the document summarizer tool"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "execute", **kwargs)
        
        try:
            # Get parameters
            file_data = kwargs.get("file_data")
            file_type = kwargs.get("file_type")
            
            if not file_data:
                logger.error("No file data provided")
                log_function_exit(logger, "execute", result="no_file_data")
                return {
                    "success": False,
                    "error": "No file data provided"
                }
            
            if not file_type:
                logger.error("File type not specified")
                log_function_exit(logger, "execute", result="no_file_type")
                return {
                    "success": False,
                    "error": "File type not specified"
                }
            
            # Decode base64 file data if needed
            if isinstance(file_data, str):
                try:
                    logger.debug("Decoding base64 file data")
                    file_bytes = base64.b64decode(file_data)
                    logger.info(f"Successfully decoded base64 data: {len(file_bytes)} bytes")
                except Exception as e:
                    logger.error("Invalid base64 file data")
                    log_exception(logger, e, "execute.base64_decode")
                    log_function_exit(logger, "execute", result="invalid_base64_data")
                    return {
                        "success": False,
                        "error": "Invalid base64 file data"
                    }
            else:
                file_bytes = file_data
                logger.debug(f"Using raw file data: {len(file_bytes)} bytes")
            
            # Extract text from document
            logger.info(f"Extracting text from {file_type} document")
            extracted_text = self.extract_text(file_bytes, file_type)
            
            if not extracted_text.strip():
                logger.warning("No text content found in the document")
                log_function_exit(logger, "execute", result="no_text_content")
                return {
                    "success": False,
                    "error": "No text content found in the document"
                }
            
            # Generate summary
            logger.info("Generating summary from extracted text")
            summary = await self.summarize_text(extracted_text)
            
            result = {
                "success": True,
                "summary": summary,
                "extracted_text_length": len(extracted_text),
                "file_type": file_type
            }
            
            logger.info(f"Document summarization completed successfully: {len(summary)} characters summary")
            log_function_exit(logger, "execute", result="summarization_completed")
            return result
            
        except Exception as e:
            log_exception(logger, e, "execute")
            log_function_exit(logger, "execute", result="execution_failed")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool schema for MCP registration"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "get_schema")
        
        try:
            schema = {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_data": {
                            "type": "string",
                            "description": "Base64 encoded file data or raw bytes"
                        },
                        "file_type": {
                            "type": "string",
                            "enum": ["pdf", "docx"],
                            "description": "Type of the document file (pdf or docx)"
                        }
                    },
                    "required": ["file_data", "file_type"]
                }
            }
            
            log_function_exit(logger, "get_schema", result="schema_returned")
            return schema
        except Exception as e:
            log_exception(logger, e, "get_schema")
            log_function_exit(logger, "get_schema", result="schema_generation_failed")
            raise


# Requirements:
# pip install PyPDF2 python-docx langchain-google-genai pdfplumber

# Example usage
async def main():
    logger = setup_logger(__name__)
    log_function_entry(logger, "main")
    
    try:
        # Initialize the tool with your Google API key
        logger.info("Initializing DocumentSummarizerTool")
        summarizer = DocumentSummarizerTool()
        
        # Example with base64 encoded file
        logger.info("Reading example PDF file")
        with open("Documents\Drashti Parmar Resume.pdf", "rb") as f:
            file_bytes = f.read()
            file_data = base64.b64encode(file_bytes).decode('utf-8')
        
        logger.info("Executing document summarization")
        result = await summarizer.execute(
            file_data=file_data,
            file_type="pdf"
        )
        
        if result["success"]:
            logger.info("Document summarization completed successfully")
            print("Summary:", result["summary"])
            print("Text length:", result["extracted_text_length"])
        else:
            logger.error(f"Document summarization failed: {result['error']}")
            print("Error:", result["error"])
        
        log_function_exit(logger, "main", result="execution_completed")
    except Exception as e:
        log_exception(logger, e, "main")
        log_function_exit(logger, "main", result="execution_failed")
        raise
