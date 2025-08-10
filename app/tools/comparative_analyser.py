import os
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from typing import Any, Dict, List
from .base_tool import BaseMCPTool
import pdfplumber
from docx import Document
import numpy as np
from logger import setup_logger, log_exception, log_function_entry, log_function_exit

logger = setup_logger(__name__)

class ComparativeAnalyzer(BaseMCPTool):
    def __init__(self):
        log_function_entry(logger, "__init__")
        try:
            super().__init__(
                name="comparative_analysis",
                description="Compare financial data across multiple PDF/DOCX documents by extracting and analyzing tables"
            )
            logger.info("ComparativeAnalyzer initialized successfully")
            log_function_exit(logger, "__init__", result="initialization_successful")
        except Exception as e:
            log_exception(logger, e, "ComparativeAnalyzer initialization")
            log_function_exit(logger, "__init__", result="initialization_failed")
            raise
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "Unique identifier for the message/request"
                        },
                        "documents": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "file_path": {
                                        "type": "string", 
                                        "description": "Path to the document file or base64 encoded file data"
                                    },
                                    "document_type": {
                                        "type": "string", 
                                        "enum": ["pdf", "docx"], 
                                        "description": "Document type - either 'pdf' or 'docx'"
                                    },
                                    "document_name": {
                                        "type": "string", 
                                        "description": "Name/identifier for the document"
                                    },
                                    "file_data": {
                                        "type": "string", 
                                        "description": "Base64 encoded file data (optional if file_path is provided)"
                                    }
                                },
                                "required": ["document_type", "document_name"]
                            }
                        },
                        "comparison_columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific columns to compare (optional)",
                            "default": []
                        }
                    },
                    "required": ["message_id", "documents"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        log_function_entry(logger, "execute")
        try:
            message_id = kwargs.get('message_id')
            documents = kwargs.get('documents', [])
            comparison_columns = kwargs.get('comparison_columns', [])
            
            if not documents:
                raise Exception("No documents provided for analysis")
            if len(documents) < 2:
                raise Exception("At least 2 documents are required for comparison")
            
            processed_documents = await self._prepare_documents(documents)
            document_tables = await self._extract_tables_from_documents(processed_documents)
            comparable_data = self._identify_comparable_data(document_tables, comparison_columns)
            analysis_results = self._perform_comparative_analysis(comparable_data)
            chart_base64 = self._create_comparison_chart(analysis_results, message_id)
            insights = self._generate_comparison_insights(analysis_results)
            
            result = {
                "success": True,
                "data": {
                    "insights": insights,
                    "analysis_results": analysis_results,
                    "chart_saved": f"{message_id}.png" if chart_base64 else None
                }
            }
            
            log_function_exit(logger, "execute", result=result)
            return result
            
        except Exception as e:
            log_exception(logger, e, "Comparative analysis execution")
            result = {"success": False, "error": str(e)}
            log_function_exit(logger, "execute", result=result)
            return result
    
    async def _prepare_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        processed_documents = []
        
        for i, doc in enumerate(documents):
            try:
                if 'document_type' not in doc:
                    raise ValueError(f"Document {i+1}: 'document_type' is required")
                if 'document_name' not in doc:
                    raise ValueError(f"Document {i+1}: 'document_name' is required")
                
                document_type = doc['document_type'].lower()
                if document_type not in ['pdf', 'docx']:
                    raise ValueError(f"Document {i+1}: document_type must be 'pdf' or 'docx'")
                
                file_data = None
                if 'file_data' in doc and doc['file_data']:
                    file_data = doc['file_data']
                elif 'file_path' in doc and doc['file_path']:
                    file_data = await self._read_file_to_base64(doc['file_path'])
                else:
                    raise ValueError(f"Document {i+1}: Either 'file_data' or 'file_path' must be provided")
                
                processed_documents.append({
                    'document_name': doc['document_name'],
                    'file_type': document_type,
                    'file_data': file_data
                })
                
            except Exception as e:
                raise Exception(f"Document {i+1} ({doc.get('document_name', 'unknown')}): {str(e)}")
        
        return processed_documents
    
    async def _read_file_to_base64(self, file_path: str) -> str:
        try:
            with open(file_path, 'rb') as file:
                file_content = file.read()
                return base64.b64encode(file_content).decode('utf-8')
        except FileNotFoundError:
            raise Exception(f"File not found: {file_path}")
        except Exception as e:
            raise Exception(f"Error reading file {file_path}: {str(e)}")
    
    async def _extract_tables_from_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        document_tables = {}
        for doc in documents:
            doc_name = doc['document_name']
            file_data = doc['file_data']
            file_type = doc['file_type']
            
            try:
                if file_type.lower() == 'pdf':
                    tables = self._extract_tables_from_pdf(file_data)
                elif file_type.lower() == 'docx':
                    tables = self._extract_tables_from_docx(file_data)
                else:
                    tables = []
                
                document_tables[doc_name] = {
                    'tables': tables,
                    'table_count': len(tables),
                    'file_type': file_type
                }
            except Exception as e:
                document_tables[doc_name] = {
                    'tables': [],
                    'table_count': 0,
                    'error': str(e),
                    'file_type': file_type
                }
        return document_tables
    
    def _extract_tables_from_pdf(self, file_data: str) -> List[pd.DataFrame]:
        tables = []
        try:
            file_bytes = base64.b64decode(file_data)
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    try:
                        page_tables = page.extract_tables()
                        for table in page_tables:
                            if table and len(table) > 1:
                                df = pd.DataFrame(table[1:], columns=table[0])
                                df = self._clean_extracted_table(df)
                                if not df.empty:
                                    tables.append(df)
                    except Exception:
                        continue
        except Exception as e:
            raise Exception(f"Failed to extract tables from PDF: {str(e)}")
        return tables
    
    def _extract_tables_from_docx(self, file_data: str) -> List[pd.DataFrame]:
        tables = []
        try:
            file_bytes = base64.b64decode(file_data)
            doc = Document(BytesIO(file_bytes))
            for table in doc.tables:
                try:
                    table_data = []
                    for row in table.rows:
                        row_data = [cell.text.strip() for cell in row.cells]
                        table_data.append(row_data)
                    
                    if len(table_data) > 1:
                        df = pd.DataFrame(table_data[1:], columns=table_data[0])
                        df = self._clean_extracted_table(df)
                        if not df.empty:
                            tables.append(df)
                except Exception:
                    continue
        except Exception as e:
            raise Exception(f"Failed to extract tables from DOCX: {str(e)}")
        return tables
    
    def _clean_extracted_table(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        
        df = df.dropna(how='all').dropna(axis=1, how='all')
        df.columns = df.columns.str.strip().str.lower()
        
        for col in df.columns:
            if col not in ['description', 'item', 'category', 'account']:
                df[col] = df[col].astype(str).str.replace(r'[$,()%]', '', regex=True)
                df[col] = df[col].str.replace('−', '-')
                df[col] = pd.to_numeric(df[col].replace('[^0-9.-]', '', regex=True), errors='coerce')
        
        return df
    
    def _identify_comparable_data(self, document_tables: Dict[str, Any], 
                                 comparison_columns: List[str]) -> Dict[str, Any]:
        comparable_data = {
            'matched_tables': {},
            'common_columns': [],
            'columns_to_compare': comparison_columns,
            'all_numerical_columns': set()
        }
        
        financial_keywords = ['revenue', 'expense', 'profit', 'income', 'cost', 'total', 'amount']
        
        for doc_name, doc_data in document_tables.items():
            tables = doc_data.get('tables', [])
            matched_tables = []
            
            for i, table in enumerate(tables):
                if self._is_financial_table(table, financial_keywords):
                    numerical_cols = table.select_dtypes(include=[np.number]).columns.tolist()
                    comparable_data['all_numerical_columns'].update(numerical_cols)
                    
                    matched_tables.append({
                        'table_index': i,
                        'table_data': table,
                        'columns': list(table.columns),
                        'numerical_columns': numerical_cols,
                        'shape': table.shape
                    })
            
            comparable_data['matched_tables'][doc_name] = matched_tables
        
        # Identify common columns across all documents
        all_columns = []
        for doc_name, tables in comparable_data['matched_tables'].items():
            for table_info in tables:
                all_columns.extend(table_info['columns'])
        
        column_counts = {}
        for col in all_columns:
            column_counts[col] = column_counts.get(col, 0) + 1
        
        comparable_data['common_columns'] = [col for col, count in column_counts.items() if count > 1]
        comparable_data['all_numerical_columns'] = list(comparable_data['all_numerical_columns'])
        
        return comparable_data
    
    def _is_financial_table(self, df: pd.DataFrame, financial_keywords: List[str]) -> bool:
        if df.empty:
            return False
        
        columns_text = ' '.join(df.columns).lower()
        for keyword in financial_keywords:
            if keyword in columns_text:
                return True
        
        numeric_cols = df.select_dtypes(include=['number']).columns
        return len(numeric_cols) > 0
    
    def _perform_comparative_analysis(self, comparable_data: Dict[str, Any]) -> Dict[str, Any]:
        analysis_results = {
            'document_comparison': {},
            'column_comparison': {},
            'percentage_changes': {},
            'trends': [],
            'columns_analyzed': []
        }
        
        matched_tables = comparable_data['matched_tables']
        comparison_columns = comparable_data['columns_to_compare']
        
        # Determine which columns to analyze
        if comparison_columns:
            # Use specified comparison columns
            columns_to_analyze = comparison_columns
        else:
            # Use all common numerical columns
            columns_to_analyze = comparable_data.get('common_columns', [])
            # Filter to only numerical columns
            all_numerical = comparable_data.get('all_numerical_columns', [])
            columns_to_analyze = [col for col in columns_to_analyze if col in all_numerical]
        
        analysis_results['columns_analyzed'] = columns_to_analyze
        
        # Initialize document comparison structure
        for doc_name in matched_tables.keys():
            analysis_results['document_comparison'][doc_name] = {
                'columns': {},
                'total_across_all_columns': 0
            }
        
        # Analyze each column
        for column in columns_to_analyze:
            column_totals = {}
            
            for doc_name, tables in matched_tables.items():
                total_value = 0
                found_in_tables = []
                
                for table_info in tables:
                    table = table_info['table_data']
                    if column in table.columns:
                        numeric_values = pd.to_numeric(table[column], errors='coerce').dropna()
                        if not numeric_values.empty:
                            table_total = numeric_values.sum()
                            total_value += table_total
                            found_in_tables.append({
                                'table_index': table_info['table_index'],
                                'values': numeric_values.tolist(),
                                'total': table_total
                            })
                
                if total_value > 0:
                    column_totals[doc_name] = total_value
                    analysis_results['document_comparison'][doc_name]['columns'][column] = {
                        'total_value': total_value,
                        'table_count': len(found_in_tables),
                        'detailed_breakdown': found_in_tables
                    }
                    analysis_results['document_comparison'][doc_name]['total_across_all_columns'] += total_value
            
            # Calculate percentage changes between documents
            if len(column_totals) >= 2:
                doc_names = list(column_totals.keys())
                for i in range(len(doc_names) - 1):
                    doc1 = doc_names[i]
                    doc2 = doc_names[i + 1]
                    val1 = column_totals[doc1]
                    val2 = column_totals[doc2]
                    
                    comparison_key = f"{column}_{doc1}_vs_{doc2}"
                    
                    if val1 > 0:
                        percentage_change = ((val2 - val1) / val1) * 100
                        analysis_results['percentage_changes'][comparison_key] = {
                            'column': column,
                            'from_value': val1,
                            'to_value': val2,
                            'percentage_change': round(percentage_change, 2),
                            'absolute_change': val2 - val1,
                            'trend': 'increase' if percentage_change > 0 else 'decrease' if percentage_change < 0 else 'stable'
                        }
            
            # Store column comparison summary
            if column_totals:
                analysis_results['column_comparison'][column] = {
                    'highest_document': max(column_totals, key=column_totals.get),
                    'lowest_document': min(column_totals, key=column_totals.get),
                    'total_across_docs': sum(column_totals.values()),
                    'average_across_docs': sum(column_totals.values()) / len(column_totals),
                    'document_count': len(column_totals)
                }
        
        return analysis_results
    
    def _create_comparison_chart(self, analysis_results: Dict[str, Any], message_id: str) -> str:
        doc_comparison = analysis_results.get('document_comparison', {})
        columns_analyzed = analysis_results.get('columns_analyzed', [])
        
        if not doc_comparison or not columns_analyzed:
            return None
        
        doc_names = list(doc_comparison.keys())
        
        if len(columns_analyzed) == 1:
            fig, ax = plt.subplots(figsize=(12, 8))
            column = columns_analyzed[0]
            values = []
            for doc_name in doc_names:
                doc_data = doc_comparison[doc_name]
                if column in doc_data.get('columns', {}):
                    values.append(doc_data['columns'][column]['total_value'])
                else:
                    values.append(0)
            
            bars = ax.bar(doc_names, values, color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'][:len(doc_names)])
            ax.set_title(f'{column.title()} Comparison Across Documents', fontsize=16, fontweight='bold')
            ax.set_xlabel('Documents')
            ax.set_ylabel(f'{column.title()} Amount')
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.annotate(f'${value:,.0f}', 
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 5), textcoords="offset points",
                           ha='center', va='bottom', fontweight='bold')
            
            plt.xticks(rotation=45, ha='right')
            
        else:
            fig, ax = plt.subplots(figsize=(14, 8))
            x = np.arange(len(doc_names))
            width = 0.8 / len(columns_analyzed)
            colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#8B5CF6', '#10B981']
            
            for i, column in enumerate(columns_analyzed):
                values = []
                for doc_name in doc_names:
                    doc_data = doc_comparison[doc_name]
                    if column in doc_data.get('columns', {}):
                        values.append(doc_data['columns'][column]['total_value'])
                    else:
                        values.append(0)
                
                bars = ax.bar(x + i * width - width * (len(columns_analyzed) - 1) / 2, 
                             values, width, label=column.title(), color=colors[i % len(colors)])
                
                for bar, value in zip(bars, values):
                    height = bar.get_height()
                    if height > 0:
                        ax.annotate(f'${value:,.0f}', 
                                   xy=(bar.get_x() + bar.get_width() / 2, height),
                                   xytext=(0, 3), textcoords="offset points",
                                   ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            ax.set_title('Multi-Column Comparison Across Documents', fontsize=16, fontweight='bold')
            ax.set_xlabel('Documents')
            ax.set_ylabel('Amount')
            ax.set_xticks(x)
            ax.set_xticklabels(doc_names, rotation=45, ha='right')
            ax.legend()
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        plt.tight_layout()
        
        # Save chart with message_id as filename
        os.makedirs("charts", exist_ok = True)
        plt.savefig(f"charts\{message_id}.png", format='png', dpi=300, bbox_inches='tight')
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        chart_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return chart_base64
    
    def _generate_comparison_insights(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        insights = {
            "key_findings": [],
            "trends": [],
            "recommendations": [],
            "data_quality": {},
            "column_insights": {}
        }
        
        doc_comparison = analysis_results.get('document_comparison', {})
        column_comparison = analysis_results.get('column_comparison', {})
        percentage_changes = analysis_results.get('percentage_changes', {})
        columns_analyzed = analysis_results.get('columns_analyzed', [])
        
        # Generate insights for each analyzed column
        for column in columns_analyzed:
            column_insights = []
            if column in column_comparison:
                column_data = column_comparison[column]
                highest_doc = column_data.get('highest_document')
                lowest_doc = column_data.get('lowest_document')
                
                if highest_doc and lowest_doc and highest_doc != lowest_doc:
                    column_insights.append(f"Highest {column}: {highest_doc}")
                    column_insights.append(f"Lowest {column}: {lowest_doc}")
            
            insights["column_insights"][column] = column_insights
        
        insights["key_findings"].append(f"Analyzed {len(columns_analyzed)} columns across {len(doc_comparison)} documents")
        
        # Analyze trends from percentage changes
        for comparison, change_data in percentage_changes.items():
            pct_change = change_data['percentage_change']
            trend = change_data['trend']
            column = change_data['column']
            
            if abs(pct_change) > 20:
                insights["trends"].append(f"Significant {trend} of {abs(pct_change):.1f}% in {column}")
            elif abs(pct_change) > 5:
                insights["trends"].append(f"Moderate {trend} of {abs(pct_change):.1f}% in {column}")
            else:
                insights["trends"].append(f"Stable {column} with minimal change")
        
        # Generate recommendations
        significant_changes = [change for change in percentage_changes.values() 
                             if abs(change['percentage_change']) > 20]
        
        if significant_changes:
            columns_with_changes = [change['column'] for change in significant_changes]
            insights["recommendations"].append(f"Investigate significant changes in: {', '.join(set(columns_with_changes))}")
        elif len(columns_analyzed) > 1:
            insights["recommendations"].append("Monitor trends across all analyzed columns for consistency")
        else:
            insights["recommendations"].append("Consider expanding analysis to include additional columns")
        
        # Data quality assessment
        total_tables = sum(len(data.get('tables', [])) for data in doc_comparison.values())
        successful_extractions = sum(1 for data in doc_comparison.values() if data.get('columns'))
        
        insights["data_quality"] = {
            "total_tables_found": total_tables,
            "successful_documents": successful_extractions,
            "total_documents": len(doc_comparison),
            "columns_analyzed": len(columns_analyzed),
            "extraction_success_rate": f"{(successful_extractions / len(doc_comparison)) * 100:.1f}%" if doc_comparison else "0%"
        }
        
        return insights

async def main():
    log_function_entry(logger, "main")
    try:
        logger.info("Starting main comparative analysis test.")
        documents = [
            {
                "file_data": "JVBERi0xLjQKJZOMi54gUmVwb3J0TGFiIEdlbmVyYXRlZCBQREYgZG9jdW1lbnQgaHR0cDovL3d3dy5yZXBvcnRsYWIuY29tCjEgMCBvYmoKPDwKL0YxIDIgMCBSIC9GMiAzIDAgUgo+PgplbmRvYmoKMiAwIG9iago8PAovQmFzZUZvbnQgL0hlbHZldGljYSAvRW5jb2RpbmcgL1dpbkFuc2lFbmNvZGluZyAvTmFtZSAvRjEgL1N1YnR5cGUgL1R5cGUxIC9UeXBlIC9Gb250Cj4+CmVuZG9iagozIDAgb2JqCjw8Ci9CYXNlRm9udCAvSGVsdmV0aWNhLUJvbGQgL0VuY29kaW5nIC9XaW5BbnNpRW5jb2RpbmcgL05hbWUgL0YyIC9TdWJ0eXBlIC9UeXBlMSAvVHlwZSAvRm9udAo+PgplbmRvYmoKNCAwIG9iago8PAovQ29udGVudHMgOCAwIFIgL01lZGlhQm94IFsgMCAwIDYxMiA3OTIgXSAvUGFyZW50IDcgMCBSIC9SZXNvdXJjZXMgPDwKL0ZvbnQgMSAwIFIgL1Byb2NTZXQgWyAvUERGIC9UZXh0IC9JbWFnZUIgL0ltYWdlQyAvSW1hZ2VJIF0KPj4gL1JvdGF0ZSAwIC9UcmFucyA8PAoKPj4gCiAgL1R5cGUgL1BhZ2UKPj4KZW5kb2JqCjUgMCBvYmoKPDwKL1BhZ2VNb2RlIC9Vc2VOb25lIC9QYWdlcyA3IDAgUiAvVHlwZSAvQ2F0YWxvZwo+PgplbmRvYmoKNiAwIG9iago8PAovQXV0aG9yIChcKGFub255bW91c1wpKSAvQ3JlYXRpb25EYXRlIChEOjIwMjUwODA5MDgyNDU5KzA1JzAwJykgL0NyZWF0b3IgKFwodW5zcGVjaWZpZWRcKSkgL0tleXdvcmRzICgpIC9Nb2REYXRlIChEOjIwMjUwODA5MDgyNDU5KzA1JzAwJykgL1Byb2R1Y2VyIChSZXBvcnRMYWIgUERGIExpYnJhcnkgLSB3d3cucmVwb3J0bGFiLmNvbSkgCiAgL1N1YmplY3QgKFwodW5zcGVjaWZpZWRcKSkgL1RpdGxlIChcKGFub255bW91c1wpKSAvVHJhcHBlZCAvRmFsc2UKPj4KZW5kb2JqCjcgMCBvYmoKPDwKL0NvdW50IDEgL0tpZHMgWyA0IDAgUiBdIC9UeXBlIC9QYWdlcwo+PgplbmRvYmoKOCAwIG9iago8PAovRmlsdGVyIFsgL0FTQ0lJODVEZWNvZGUgL0ZsYXRlRGVjb2RlIF0gL0xlbmd0aCA5ODEKPj4Kc3RyZWFtCkdhc2FvRC9ZbXQmSDg4LkVNJzg0OGoxcDoiNTo1ZG1BK0hbZzY9Z1AmZ3NAXE85NFtpXlldb0Y2YU9eZjpyOz5eXGIjRmYlTkdaZTBAa1ApJEBxUm9JKGExLjMyQSc0K1VLPWolPHEndEFcbmoyTUVyUi9fPEBZYlk/ayFZTk9fWks7ZF49TS9DbWZcZi80RCk4MTZlNVZiPEU2a0BJW0hublxcVFtCJlIuMzk6MCdBRDZrXWtxZi1lRTpZTF4zQlo8b1I3QHMrKmYmVWZZa3BoRzk/aT86PldSUjxGMGJwVVJWcVsjPGZVNTpkb29hbzpNbDwhMmQ/M2UlQ0AmWDQmb2RoNWQ1aVRlW1pHcVotMTkjYTsvcEsxbHVSYFIoXV1eQVdOaWpoJTZXJjNgaU1iZ2FjTFllUV1aJVYyP2ZXZUluPE9BXXAsUF1dSj9fPCtWOGdWZWRNMD9XR1BqQkpzUEFdSVBoUF0pO2g5XFYpMC1zL0l0MWY/ZFImZystRU9oc1A6QVE7ZDduWDMlRWowZlpiMlMwJSlFQSI1cSwiOmI1KyxfRTxpMSx1cFZzJUFvdStwX1hMS1MxOWNUZSc7TzpJbFtEJ1NrVzdaL2ViMUNlZDwmJENXPj9iZTUrKURRXlMtb3Q8YUZVSFY+MEZsUEZaT2dTcTBlSzYkXEBpUXMrKlMqKC4zIyNxZFFvalpqcWJFRTlDLzA6aDYiRC9acU90Jm1IJF5PUyImPiJpK0U7TjM6S1ZzaCFoQ1RIb0gyXVhfanA2UTM9UGJoYy9SQ05XMm9YNToyQ1JnNiJpUSNgW1JIVThsJiJAIU1McHRUVldHRDteMTdbVEtNOVxqR25sXjVRZjo8VmlDZkxRPVYyJT85QG1xMl10IWQwJSJSYGRgOWRMXkJBO1k+N1UzKm0yIW5EZy1hRywldCooPyNsRiY/QSRkMl5vVztyOj5BLnReXUIoMFJIMGxCanI3XltYaEohTEtnKCE3NG0wNTAlb0BhWFE3ZCUwYCVSLWlBRFIkby1BYl91NzMkS0B1WGtJVVdTYnVmVzAnPVwqQFprXDdQS3VTYURGSSpIM05UYCRvWmElNmQvPiIocnFETjxvQls5QlQkPGFFclknZG9cSikkSiNFXHFpS3I2T2cjPDJWQlVhKTYvKiVkOzNyNWhiPGNWcyFyZ1Vjb15OY1V0NGgxNlIkQk5tRnBZOFl1Tk5FWlxFMjgqYUMlOmc7Y3E/NTdqQHViIjFlTk4vK11mRiJqUWhuZU4wazY1UThgNCdrQmsqNFsiZD1IIykrTGt+PmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDkKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDczIDAwMDAwIG4gCjAwMDAwMDAxMTQgMDAwMDAgbiAKMDAwMDAwMDIyMSAwMDAwMCBuIAowMDAwMDAwMzMzIDAwMDAwIG4gCjAwMDAwMDA1MjYgMDAwMDAgbiAKMDAwMDAwMDU5NCAwMDAwMCBuIAowMDAwMDAwODc3IDAwMDAwIG4gCjAwMDAwMDA5MzYgMDAwMDAgbiAKdHJhaWxlcgo8PAovSUQgCls8ODYyOTM0YWQ1MDliMzEyNDdkMGJhNzUzYTIzNmY5ZDY+PDg2MjkzNGFkNTA5YjMxMjQ3ZDBiYTc1M2EyMzZmOWQ2Pl0KJSBSZXBvcnRMYWIgZ2VuZXJhdGVkIFBERiBkb2N1bWVudCAtLSBkaWdlc3QgKGh0dHA6Ly93d3cucmVwb3J0bGFiLmNvbSkKCi9JbmZvIDYgMCBSCi9Sb290IDUgMCBSCi9TaXplIDkKPj4Kc3RhcnR4cmVmCjIwMDcKJSVFT0YK",
                "file_type": "pdf", 
                "document_name": "Financial_Report_2023"
            },
            {
                "file_data": "JVBERi0xLjQKJZOMi54gUmVwb3J0TGFiIEdlbmVyYXRlZCBQREYgZG9jdW1lbnQgaHR0cDovL3d3dy5yZXBvcnRsYWIuY29tCjEgMCBvYmoKPDwKL0YxIDIgMCBSIC9GMiAzIDAgUgo+PgplbmRvYmoKMiAwIG9iago8PAovQmFzZUZvbnQgL0hlbHZldGljYSAvRW5jb2RpbmcgL1dpbkFuc2lFbmNvZGluZyAvTmFtZSAvRjEgL1N1YnR5cGUgL1R5cGUxIC9UeXBlIC9Gb250Cj4+CmVuZG9iagozIDAgb2JqCjw8Ci9CYXNlRm9udCAvSGVsdmV0aWNhLUJvbGQgL0VuY29kaW5nIC9XaW5BbnNpRW5jb2RpbmcgL05hbWUgL0YyIC9TdWJ0eXBlIC9UeXBlMSAvVHlwZSAvRm9udAo+PgplbmRvYmoKNCAwIG9iago8PAovQ29udGVudHMgOCAwIFIgL01lZGlhQm94IFsgMCAwIDYxMiA3OTIgXSAvUGFyZW50IDcgMCBSIC9SZXNvdXJjZXMgPDwKL0ZvbnQgMSAwIFIgL1Byb2NTZXQgWyAvUERGIC9UZXh0IC9JbWFnZUIgL0ltYWdlQyAvSW1hZ2VJIF0KPj4gL1JvdGF0ZSAwIC9UcmFucyA8PAoKPj4gCiAgL1R5cGUgL1BhZ2UKPj4KZW5kb2JqCjUgMCBvYmoKPDwKL1BhZ2VNb2RlIC9Vc2VOb25lIC9QYWdlcyA3IDAgUiAvVHlwZSAvQ2F0YWxvZwo+PgplbmRvYmoKNiAwIG9iago8PAovQXV0aG9yIChcKGFub255bW91c1wpKSAvQ3JlYXRpb25EYXRlIChEOjIwMjUwODA5MDgyNDU5KzA1JzAwJykgL0NyZWF0b3IgKFwodW5zcGVjaWZpZWRcKSkgL0tleXdvcmRzICgpIC9Nb2REYXRlIChEOjIwMjUwODA5MDgyNDU5KzA1JzAwJykgL1Byb2R1Y2VyIChSZXBvcnRMYWIgUERGIExpYnJhcnkgLSB3d3cucmVwb3J0bGFiLmNvbSkgCiAgL1N1YmplY3QgKFwodW5zcGVjaWZpZWRcKSkgL1RpdGxlIChcKGFub255bW91c1wpKSAvVHJhcHBlZCAvRmFsc2UKPj4KZW5kb2JqCjcgMCBvYmoKPDwKL0NvdW50IDEgL0tpZHMgWyA0IDAgUiBdIC9UeXBlIC9QYWdlcwo+PgplbmRvYmoKOCAwIG9iago8PAovRmlsdGVyIFsgL0FTQ0lJODVEZWNvZGUgL0ZsYXRlRGVjb2RlIF0gL0xlbmd0aCA5ODkKPj4Kc3RyZWFtCkdhc2JaZ04pIiUmO0tZIU1TODwlJHJKPFJaRTxAc1MicWoyRnNbSS9KN0QiLCdeU2RZOGI7WF1sXChJUmInOl4ycFhCIT1bMCIwcGlsMTgyWk45aSFfNUBZRk4nanVTLUFbMzsjRm5sJWhfWEU6VTRjY2tLSj5yNWJoVUheKU4wbCJjM0M9Z0AtKExFbzxBTHAiVkZYP1xsdXVLVUAlNktDJFJXXWxjN2lqXmFXYFpvZjJkUmVIOGJ1RTtGL1JDOk0uSFhjPmAsM28zQVxFOWM7OUBURjVNPi0oKFBDJ3Q1Uj9KVEJFX0RqaE5ZTF45JltTWGtiMFJcLyNPZiFXWmpxVXBvaG5aIiRITlVJXzJWU0RKWyk1JjY/Ijd1aWVQIi1aWCoxRltnTj5UajZKWDU1bWRkQCliQCMxaXMjZlJhWDEmNEwjI2MnL1kmMGg8WVBZMTxnOmkzNUxNUClZNUZkLzEiWkVkYVYyI2d0MWpxPE1wQGA0OSM5aTdDWWVANiJMLSpsISUvMiMwQigpMSJyO0UnPWBfIiE0MT9tQUw4Qk9vV2k7RlxuZ2wydEwhRWtnKFJEVUksY2wvdVxBamthZi1qQFA5UklgYmQwTHNNTSJjIT5bcHEsOVVHNXAyOVxYb0xdOE8lOj9mblJlZU5pVWQkZjg4Wj5MWCY6dVlQIzZpVChJSUdEMzl1T3A9c2xVISppLVouaUlTRWdbWTRuY1QiZDotZlcjXWdnS08yIUV1SE9yQTQwR3JMRStyRG11RzcvSmNDSChVaSQ0NDBWRDtBME85VF8nRTtfOGU1JWUpNTFhImRvKiFvUCozSGRCWy41PShSdGFQMjVJNmE+UyduKSJZKk47SlEwb1U6S2RFJz5CIm5BRlxnM1lzNDA/JVZ1MWYqNXNvRFcxWDY8KTsjcz1oN0lQZ2dtb2RmRkxYPm9RRD4xRDJaSGcnUE1raW8sNF9SQjVHQVspVVAiRnQlRjROZSZccWM7Xl07TF9DbksscVI0MmI+NilIKDZeSFhMUik0Mltbbk0qJlk9PEJvIiFqTW5acj1IcG8yP21TWjRlRHB1b1I9R1laXmBvOT4sQmdlKlhIXENKbkxeNC5vOjZ0IVpnW1s4bkBzbjVoc2VOVjRLZ1slcF9jO3RpUG01Li9ray4qa2xjcFtoQGFROT0xXVokUmA3JUE2USNqSGAlWzM9MzZRTVMqLz82SUhlTFdob08wMmhZKVE1IlVSYDdBZlFfaykuNmo/YCQ5SW4hazFqcEJqI2VDb1MyJzJeUEZUZCljNCovL2IkSGUhJF0zTSJVJn4+ZW5kc3RyZWFtCmVuZG9iagp4cmVmCjAgOQowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwNzMgMDAwMDAgbiAKMDAwMDAwMDExNCAwMDAwMCBuIAowMDAwMDAwMjIxIDAwMDAwIG4gCjAwMDAwMDAzMzMgMDAwMDAgbiAKMDAwMDAwMDUyNiAwMDAwMCBuIAowMDAwMDAwNTk0IDAwMDAwIG4gCjAwMDAwMDA4NzcgMDAwMDAgbiAKMDAwMDAwMDkzNiAwMDAwMCBuIAp0cmFpbGVyCjw8Ci9JRCAKWzxhNmFlMmVhMDFmYTE2NWFiYjhkZmJiZWRiZWEzYWFkOT48YTZhZTJlYTAxZmExNjVhYmI4ZGZiYmVkYmVhM2FhZDk+XQolIFJlcG9ydExhYiBnZW5lcmF0ZWQgUERGIGRvY3VtZW50IC0tIGRpZ2VzdCAoaHR0cDovL3d3dy5yZXBvcnRsYWIuY29tKQoKL0luZm8gNiAwIFIKL1Jvb3QgNSAwIFIKL1NpemUgOQo+PgpzdGFydHhyZWYKMjAxNQolJUVPRgo=",
                "file_type": "pdf",
                "document_name": "Financial_Report_2022"
            }
        ]
        # User query: "compare the total expenses between the 2023 and 2022 financial reports"
        result = await ComparativeAnalyzer().execute(
            documents=documents,
            # comparison_metric=["expense", "revenue", "Profit"]
        )
        # logger.info(f"Comparative analysis result: {result}")
        with open("result.txt", "w", encoding="utf-8") as f:
            f.write(str(result))
        log_function_exit(logger, "main", result=result)

    except Exception as e:
        log_exception(logger, e, "Error during analysis")
        log_function_exit(logger, "main", result={"success": False, "error": str(e), "message": "Failed to perform comparative analysis"})

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
