import json
from typing import Dict, List, Any
from tools.financial_trend_analyser import FinancialTrendAnalyzer
from tools.comparative_analyser import ComparativeAnalyzer
from tools.document_summarizer import DocumentSummarizerTool
from tools.table_extractor import DataExtractionTool
from tools.web_researcher import WebQueryTool
from tools.statistical_analyzer import StatisticalAnalyzer
from tools.general_query import GeneralQuery
from logger import setup_logger, log_exception, log_function_entry, log_function_exit

logger = setup_logger(__name__)

class MCPServer:
    def __init__(self):
        log_function_entry(logger, "__init__")
        try:
            self.tools = {
                "financial_trend_analysis": FinancialTrendAnalyzer(),
                "document_summarizer": DocumentSummarizerTool(),
                "extract_table_data": DataExtractionTool(),
                "comparative_analysis": ComparativeAnalyzer(),
                "web_research": WebQueryTool(),
                "statistical_analysis": StatisticalAnalyzer(),
                "general_query": GeneralQuery()
            }
            logger.info(f"MCPServer initialized with {len(self.tools)} tools")
            log_function_exit(logger, "__init__", result="initialization_successful")
        except Exception as e:
            log_exception(logger, e, "MCPServer initialization")
            log_function_exit(logger, "__init__", result="initialization_failed")
            raise
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Return list of available tools with their schemas"""
        log_function_entry(logger, "get_available_tools")
        try:
            tools_list = [tool.get_schema() for tool in self.tools.values()]
            logger.debug(f"Retrieved {len(tools_list)} available tools")
            log_function_exit(logger, "get_available_tools", result=f"tools_count={len(tools_list)}")
            return tools_list
        except Exception as e:
            log_exception(logger, e, "get_available_tools")
            log_function_exit(logger, "get_available_tools", result="error")
            return []
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific tool"""
        log_function_entry(logger, "execute_tool", tool_name=tool_name, kwargs_keys=list(kwargs.keys()))
        
        try:
            if tool_name not in self.tools:
                error_msg = f"Tool {tool_name} not found"
                logger.warning(error_msg)
                log_function_exit(logger, "execute_tool", result="tool_not_found")
                return {"error": error_msg}
            
            tool = self.tools[tool_name]
            logger.info(f"Executing tool: {tool_name}")
            result = await tool.execute(**kwargs)
            
            logger.info(f"Tool {tool_name} executed successfully")
            log_function_exit(logger, "execute_tool", result="tool_executed")
            return result
            
        except Exception as e:
            log_exception(logger, e, f"execute_tool - tool_name: {tool_name}")
            log_function_exit(logger, "execute_tool", result="error")
            return {"error": f"Tool execution failed: {str(e)}"}
    
    def save_config(self, filename: str = "mcp.json"):
        """Save MCP configuration to file"""
        log_function_entry(logger, "save_config", filename=filename)
        
        try:
            config = {
                "mcpVersion": "2025-08-09",
                "servers": {
                    "financial_chatbot": {
                        "command": "python",
                        "args": ["-m", "mcp_server"],
                        "env": {}
                    }
                },
                "tools": self.get_available_tools()
            }
            
            with open(filename, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"MCP configuration saved to {filename}")
            log_function_exit(logger, "save_config", result="config_saved")
            
        except Exception as e:
            log_exception(logger, e, f"save_config - filename: {filename}")
            log_function_exit(logger, "save_config", result="error")
            raise

# Create global MCP server instance
mcp_server = MCPServer()
