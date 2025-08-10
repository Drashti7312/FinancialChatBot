import pandas as pd
import numpy as np
from typing import Any, Dict, Union, Optional
from .base_tool import BaseMCPTool
from logger import setup_logger, log_exception, log_function_entry, log_function_exit
import base64
from io import BytesIO

class DataExtractionTool(BaseMCPTool):
    def __init__(self):
        log_function_entry(setup_logger(__name__), "DataExtractionTool.__init__")
        
        try:
            super().__init__(
                name="extract_table_data",
                description="Extracts specific data points and top entries from tables and structured data"
            )
            logger = setup_logger(__name__)
            logger.info("DataExtractionTool initialized successfully")
            log_function_exit(setup_logger(__name__), "DataExtractionTool.__init__", result="initialization_completed")
        except Exception as e:
            log_exception(setup_logger(__name__), e, "DataExtractionTool.__init__")
            raise
    
    def _load_data_from_bytes(self, file_data: str, file_type: str, sheet_name: Optional[str] = None) -> pd.DataFrame:        
        try:
            if isinstance(file_data, bytes):
                file_bytes = file_data
            else:
                file_bytes = base64.b64decode(file_data)
                
            buffer = BytesIO(file_bytes)
            
            if file_type.lower() == 'csv':
                df = pd.read_csv(buffer)
            else:
                buffer.seek(0)
                engines = ['openpyxl', 'xlrd']
                df = None
                
                for engine in engines:
                    try:
                        buffer.seek(0)
                        if sheet_name:
                            df = pd.read_excel(buffer, sheet_name=sheet_name, engine=engine)
                        else:
                            df = pd.read_excel(buffer, engine=engine)
                        break
                    except Exception:
                        continue
                
                if df is None:
                    buffer.seek(0)
                    if sheet_name:
                        df = pd.read_excel(buffer, sheet_name=sheet_name)
                    else:
                        df = pd.read_excel(buffer)
            
            return df
            
        except Exception as e:
            raise Exception(f"Error loading {file_type} file: {str(e)}")
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute data extraction from tables
        
        Args:
            file_data: Base64 encoded file data
            file_type: File type ('csv', 'excel', 'xlsx', 'xls')
            extraction_type: 'top_n', 'filter', 'search', or 'aggregate'
            sort_column: column to sort by
            filter_criteria: criteria for filtering data
            n_results: number of top results to return
            ascending: sort order (True for ascending, False for descending)
            sheet_name: Excel sheet name (optional)
        """
        logger = setup_logger(__name__)
        log_function_entry(logger, "execute", **kwargs)
        
        try:
            file_data = kwargs.get('file_data')
            file_type = kwargs.get('file_type', 'excel')
            extraction_type = kwargs.get('extraction_type', 'top_n')
            sort_column = kwargs.get('sort_column', 'sales')
            filter_criteria = kwargs.get('filter_criteria', {})
            n_results = kwargs.get('n_results', 5)
            ascending = kwargs.get('ascending', False)
            sheet_name = kwargs.get('sheet_name')
            
            logger.info(f"Starting data extraction: type={extraction_type}, file_type={file_type}, sort_column={sort_column}, n_results={n_results}")
            
            # Load data using the file_type parameter
            df = self._load_data_from_bytes(file_data, file_type, sheet_name)
            logger.debug(f"Loaded DataFrame: {len(df)} rows, {len(df.columns)} columns")
            
            # Clean column names
            logger.debug("Cleaning column names")
            df.columns = df.columns.str.strip().str.lower()
            
            # Execute extraction based on type
            if extraction_type == 'top_n':
                logger.debug(f"Executing top_n extraction with sort_column={sort_column}")
                results = self._extract_top_n(df, sort_column, n_results, ascending)
            elif extraction_type == 'filter':
                logger.debug(f"Executing filter extraction with criteria={filter_criteria}")
                results = self._filter_data(df, filter_criteria)
            elif extraction_type == 'search':
                search_term = kwargs.get('search_term', '')
                logger.debug(f"Executing search extraction with search_term={search_term}")
                results = self._search_data(df, search_term)
            elif extraction_type == 'aggregate':
                group_column = kwargs.get('group_column')
                logger.debug(f"Executing aggregate extraction with group_column={group_column}")
                results = self._aggregate_data(df, group_column, sort_column)
            else:
                error_msg = f"Unknown extraction type: {extraction_type}"
                logger.error(error_msg)
                log_function_exit(logger, "execute", result="unknown_extraction_type")
                return {"success": False, "error": error_msg}
            
            # Format results
            formatted_results = self._format_results(results)
            summary = self._generate_extraction_summary(results, extraction_type, sort_column)
            
            result = {
                "success": True,
                "extraction_type": extraction_type,
                "file_type": file_type,
                "total_records": len(df),
                "extracted_records": len(results) if isinstance(results, pd.DataFrame) else len(results.get('data', [])),
                "results": formatted_results,
                "summary": summary
            }
            
            logger.info(f"Data extraction completed successfully: {result['extracted_records']} records extracted")
            log_function_exit(logger, "execute", result="extraction_completed")
            return result
            
        except Exception as e:
            log_exception(logger, e, "execute")
            log_function_exit(logger, "execute", result="extraction_failed")
            return {"success": False, "error": f"Data extraction failed: {str(e)}"}
    
    def _extract_top_n(self, df: pd.DataFrame, sort_column: str, n: int, ascending: bool) -> pd.DataFrame:
        """Extract top N records based on sort column"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "_extract_top_n", sort_column=sort_column, n=n, ascending=ascending)
        
        try:
            # Find the sort column
            sort_col = self._find_column(df, sort_column)
            if not sort_col:
                logger.warning(f"Sort column '{sort_column}' not found, using first numeric column")
                # Use first numeric column
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    sort_col = numeric_cols[0]
                    logger.info(f"Using numeric column '{sort_col}' for sorting")
                else:
                    logger.warning("No numeric columns found, returning first N records without sorting")
                    log_function_exit(logger, "_extract_top_n", result="no_sorting_applied")
                    return df.head(n)
            
            # Sort and return top N
            logger.debug(f"Sorting by column '{sort_col}' in {'ascending' if ascending else 'descending'} order")
            sorted_df = df.sort_values(sort_col, ascending=ascending)
            result = sorted_df.head(n)
            
            logger.info(f"Successfully extracted top {len(result)} records sorted by {sort_col}")
            log_function_exit(logger, "_extract_top_n", result=f"extracted_{len(result)}_records")
            return result
            
        except Exception as e:
            log_exception(logger, e, "_extract_top_n")
            log_function_exit(logger, "_extract_top_n", result="extraction_failed")
            raise
    
    def _filter_data(self, df: pd.DataFrame, filter_criteria: Dict[str, Any]) -> pd.DataFrame:
        """Filter data based on criteria"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "_filter_data", filter_criteria=filter_criteria)
        
        try:
            filtered_df = df.copy()
            initial_count = len(filtered_df)
            
            for column, criteria in filter_criteria.items():
                col = self._find_column(df, column)
                if not col:
                    logger.warning(f"Column '{column}' not found, skipping filter")
                    continue
                
                logger.debug(f"Applying filter to column '{col}' with criteria: {criteria}")
                
                if isinstance(criteria, dict):
                    # Range or condition filtering
                    if 'min' in criteria:
                        filtered_df = filtered_df[filtered_df[col] >= criteria['min']]
                        logger.debug(f"Applied min filter: {criteria['min']}")
                    if 'max' in criteria:
                        filtered_df = filtered_df[filtered_df[col] <= criteria['max']]
                        logger.debug(f"Applied max filter: {criteria['max']}")
                    if 'equals' in criteria:
                        filtered_df = filtered_df[filtered_df[col] == criteria['equals']]
                        logger.debug(f"Applied equals filter: {criteria['equals']}")
                    if 'contains' in criteria:
                        filtered_df = filtered_df[filtered_df[col].astype(str).str.contains(criteria['contains'], case=False, na=False)]
                        logger.debug(f"Applied contains filter: {criteria['contains']}")
                else:
                    # Direct value filtering
                    filtered_df = filtered_df[filtered_df[col] == criteria]
                    logger.debug(f"Applied direct filter: {criteria}")
            
            final_count = len(filtered_df)
            logger.info(f"Filtering completed: {initial_count} -> {final_count} records")
            log_function_exit(logger, "_filter_data", result=f"filtered_{final_count}_records")
            return filtered_df
            
        except Exception as e:
            log_exception(logger, e, "_filter_data")
            log_function_exit(logger, "_filter_data", result="filtering_failed")
            raise
    
    def _search_data(self, df: pd.DataFrame, search_term: str) -> pd.DataFrame:
        """Search for records containing specific terms"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "_search_data", search_term=search_term)
        
        try:
            if not search_term:
                logger.debug("No search term provided, returning all records")
                log_function_exit(logger, "_search_data", result="no_search_term")
                return df
            
            # Search across all text columns
            text_cols = df.select_dtypes(include=['object']).columns
            logger.debug(f"Searching across {len(text_cols)} text columns: {list(text_cols)}")
            
            mask = pd.Series([False] * len(df))
            
            for col in text_cols:
                mask |= df[col].astype(str).str.contains(search_term, case=False, na=False)
            
            result = df[mask]
            logger.info(f"Search completed: found {len(result)} records containing '{search_term}'")
            log_function_exit(logger, "_search_data", result=f"found_{len(result)}_records")
            return result
            
        except Exception as e:
            log_exception(logger, e, "_search_data")
            log_function_exit(logger, "_search_data", result="search_failed")
            raise
    
    def _aggregate_data(self, df: pd.DataFrame, group_column: str, metric_column: str) -> Dict[str, Any]:
        """Aggregate data by group column"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "_aggregate_data", group_column=group_column, metric_column=metric_column)
        
        try:
            group_col = self._find_column(df, group_column)
            metric_col = self._find_column(df, metric_column)
            
            if not group_col or not metric_col:
                error_msg = f"Could not find required columns for aggregation: group_column='{group_column}', metric_column='{metric_column}'"
                logger.error(error_msg)
                log_function_exit(logger, "_aggregate_data", result="columns_not_found")
                return {"error": error_msg}
            
            logger.debug(f"Aggregating data by '{group_col}' using metric '{metric_col}'")
            
            # Perform aggregation
            agg_results = df.groupby(group_col)[metric_col].agg([
                'sum', 'mean', 'count', 'min', 'max'
            ]).round(2)
            
            # Convert to dictionary format
            aggregated = {}
            for idx, row in agg_results.iterrows():
                aggregated[str(idx)] = {
                    'sum': float(row['sum']),
                    'mean': float(row['mean']),
                    'count': int(row['count']),
                    'min': float(row['min']),
                    'max': float(row['max'])
                }
            
            result = {
                "data": aggregated,
                "group_column": group_col,
                "metric_column": metric_col
            }
            
            logger.info(f"Aggregation completed: {len(aggregated)} groups")
            log_function_exit(logger, "_aggregate_data", result=f"aggregated_{len(aggregated)}_groups")
            return result
            
        except Exception as e:
            log_exception(logger, e, "_aggregate_data")
            log_function_exit(logger, "_aggregate_data", result="aggregation_failed")
            raise
    
    def _find_column(self, df: pd.DataFrame, target_col: str) -> str:
        """Find column by name with flexible matching"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "_find_column", target_col=target_col)
        
        try:
            target_lower = target_col.lower().strip()
            
            # Exact match
            if target_lower in df.columns:
                logger.debug(f"Found exact match for column '{target_col}': '{target_lower}'")
                log_function_exit(logger, "_find_column", result=f"exact_match_{target_lower}")
                return target_lower
            
            # Partial match
            for col in df.columns:
                if target_lower in col.lower() or col.lower() in target_lower:
                    logger.debug(f"Found partial match for column '{target_col}': '{col}'")
                    log_function_exit(logger, "_find_column", result=f"partial_match_{col}")
                    return col
            
            # Keyword match for common financial terms
            keyword_mapping = {
                'sales': ['sales', 'revenue', 'income'],
                'profit': ['profit', 'earnings', 'net'],
                'expense': ['expense', 'cost', 'spending'],
                'product': ['product', 'item', 'name', 'description']
            }
            
            for keyword, alternatives in keyword_mapping.items():
                if keyword in target_lower:
                    for alt in alternatives:
                        for col in df.columns:
                            if alt in col.lower():
                                logger.debug(f"Found keyword match for column '{target_col}': '{col}' (keyword: {keyword})")
                                log_function_exit(logger, "_find_column", result=f"keyword_match_{col}")
                                return col
            
            logger.warning(f"No column found matching '{target_col}'")
            log_function_exit(logger, "_find_column", result="no_match")
            return None
            
        except Exception as e:
            log_exception(logger, e, "_find_column")
            log_function_exit(logger, "_find_column", result="search_failed")
            return None
    
    def _format_results(self, results: Union[pd.DataFrame, Dict]) -> Dict[str, Any]:
        """Format results for output"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "_format_results", results_type=type(results).__name__)
        
        try:
            if isinstance(results, pd.DataFrame):
                formatted = {
                    "type": "dataframe",
                    "data": results.to_dict('records'),
                    "columns": results.columns.tolist()
                }
                logger.debug(f"Formatted DataFrame results: {len(results)} rows, {len(results.columns)} columns")
            elif isinstance(results, dict):
                formatted = {
                    "type": "aggregated",
                    "data": results
                }
                logger.debug(f"Formatted aggregated results: {len(results.get('data', {}))} groups")
            else:
                formatted = {"type": "unknown", "data": str(results)}
                logger.debug(f"Formatted unknown results type: {type(results)}")
            
            log_function_exit(logger, "_format_results", result="formatting_completed")
            return formatted
            
        except Exception as e:
            log_exception(logger, e, "_format_results")
            log_function_exit(logger, "_format_results", result="formatting_failed")
            raise
    
    def _generate_extraction_summary(self, results: Union[pd.DataFrame, Dict], extraction_type: str, sort_column: str) -> str:
        """Generate summary of extraction results"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "_generate_extraction_summary", extraction_type=extraction_type, sort_column=sort_column)
        
        try:
            if isinstance(results, pd.DataFrame):
                count = len(results)
                if extraction_type == 'top_n':
                    summary = f"Extracted top {count} records sorted by {sort_column}"
                elif extraction_type == 'filter':
                    summary = f"Found {count} records matching filter criteria"
                elif extraction_type == 'search':
                    summary = f"Found {count} records containing search terms"
                else:
                    summary = f"Extracted {count} records"
            elif isinstance(results, dict) and 'data' in results:
                if extraction_type == 'aggregate':
                    group_count = len(results['data'])
                    summary = f"Aggregated data across {group_count} groups by {results.get('group_column', 'unknown')}"
                else:
                    summary = "Data extraction completed"
            else:
                summary = "Data extraction completed"
            
            logger.debug(f"Generated summary: {summary}")
            log_function_exit(logger, "_generate_extraction_summary", result="summary_generated")
            return summary
            
        except Exception as e:
            log_exception(logger, e, "_generate_extraction_summary")
            log_function_exit(logger, "_generate_extraction_summary", result="summary_generation_failed")
            return "Data extraction completed"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool schema for MCP registration"""
        logger = setup_logger(__name__)
        log_function_entry(logger, "get_schema")
        
        try:
            schema = {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_data": {
                            "type": "string",
                            "description": "Base64 encoded file data (CSV or Excel)"
                        },
                        "file_type": {
                            "type": "string",
                            "enum": ["csv", "excel", "xlsx", "xls"],
                            "description": "Type of file being processed",
                            "default": "excel"
                        },
                        "sheet_name": {
                            "type": "string",
                            "description": "Name of the Excel sheet to analyze (optional)",
                            "default": None
                        },
                        "extraction_type": {
                            "type": "string",
                            "enum": ["top_n", "filter", "search", "aggregate"],
                            "description": "Type of data extraction to perform",
                            "default": "top_n"
                        },
                        "sort_column": {
                            "type": "string",
                            "description": "Column to sort by for top_n extraction",
                            "default": "sales"
                        },
                        "filter_criteria": {
                            "type": "object",
                            "description": "Criteria for filtering data"
                        },
                        "n_results": {
                            "type": "integer",
                            "description": "Number of top results to return",
                            "default": 5
                        },
                        "ascending": {
                            "type": "boolean",
                            "description": "Sort order (True for ascending, False for descending)",
                            "default": False
                        },
                        "search_term": {
                            "type": "string",
                            "description": "Search term for search extraction type"
                        },
                        "group_column": {
                            "type": "string",
                            "description": "Column to group by for aggregate extraction type"
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


# Example usage
async def main():
    logger = setup_logger(__name__)
    log_function_entry(logger, "main")
    
    try:
        import os
        
        # Initialize the tool
        logger.info("Initializing DataExtractionTool")
        extractor = DataExtractionTool()

        # Path to the file
        uploaded_file_path = r"Documents\FinancialTrendAnalysis2.xlsx"
        logger.info(f"Processing file: {uploaded_file_path}")

        if not os.path.exists(uploaded_file_path):
            error_msg = f"File not found: {uploaded_file_path}"
            logger.error(error_msg)
            log_function_exit(logger, "main", result="file_not_found")
            raise FileNotFoundError(error_msg)

        # Detect file type
        _, ext = os.path.splitext(uploaded_file_path)
        ext = ext.lower()
        if ext in [".xls", ".xlsx"]:
            file_type = "excel"
        elif ext == ".csv":
            file_type = "csv"
        else:
            error_msg = f"Unsupported file type: {ext}"
            logger.error(error_msg)
            log_function_exit(logger, "main", result="unsupported_file_type")
            raise ValueError(error_msg)

        logger.info(f"Detected file type: {file_type}")

        # Read and encode file
        logger.debug("Reading and encoding file")
        with open(uploaded_file_path, "rb") as f:
            file_bytes = f.read()
        file_base64 = base64.b64encode(file_bytes).decode()
        logger.info(f"Successfully encoded file: {len(file_bytes)} bytes")

        # Example 1: Extract top 5 products by sales
        logger.info("Executing top_n extraction example")
        result_top = await extractor.execute(
            file_data=file_base64,
            file_type=file_type,
            extraction_type="top_n",
            sort_column="Profit",
            n_results=5,
            ascending=False
        )
        print("\nTop N Results:")
        print(result_top)

        # Example 2: Filter data
        logger.info("Executing filter extraction example")
        filter_criteria = {
            "revenue": {"min": 5000}
        }
        result_filter = await extractor.execute(
            file_data=file_base64,
            file_type=file_type,
            extraction_type="filter",
            filter_criteria=filter_criteria
        )
        print("\nFilter Results:")
        print(result_filter)

        # Example 3: Search for all rows containing the word "Q1"
        logger.info("Executing search extraction example")
        result_search = await extractor.execute(
            file_data=file_base64,
            file_type=file_type,
            extraction_type="search",
            search_term="Q1"
        )
        print("\nSearch Results:")
        print(result_search)

        # Example 4: Aggregate sales by quarter
        logger.info("Executing aggregate extraction example")
        result_aggregate = await extractor.execute(
            file_data=file_base64,
            file_type=file_type,
            extraction_type="aggregate",
            group_column="Quarter",
            sort_column="Revenue"
        )
        print("\nAggregate Results:")
        print(result_aggregate)

        logger.info("All examples completed successfully")
        log_function_exit(logger, "main", result="examples_completed")
        
    except Exception as e:
        log_exception(logger, e, "main")
        log_function_exit(logger, "main", result="examples_failed")
        raise


if __name__=="__main__":
    import asyncio
    asyncio.run(main())