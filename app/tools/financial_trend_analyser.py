import os
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from typing import Any, Dict, List, Optional
from .base_tool import BaseMCPTool
from logger import setup_logger, log_exception, log_function_entry, log_function_exit

class FinancialTrendAnalyzer(BaseMCPTool):
    def __init__(self):
        log_function_entry(setup_logger(__name__), "FinancialTrendAnalyzer.__init__")
        try:
            super().__init__(
                name="financial_trend_analysis",
                description="Analyze financial trends from Excel/CSV data and generate insights with visualizations"
            )
            log_function_exit(setup_logger(__name__), "FinancialTrendAnalyzer.__init__", result="initialization_completed")
        except Exception as e:
            log_exception(setup_logger(__name__), e, "FinancialTrendAnalyzer.__init__")
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
                        "file_data": {
                            "type": "string",
                            "description": "Base64 encoded Excel/CSV file data"
                        },
                        "file_type": {
                            "type": "string",
                            "description": "File type: 'excel' or 'csv'",
                            "enum": ["excel", "csv"],
                            "default": "excel"
                        },
                        "sheet_name": {
                            "type": "string",
                            "description": "Name of the Excel sheet to analyze (optional)",
                            "default": None
                        },
                        "quarters": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Quarters to analyze (e.g., ['Q1', 'Q2'])",
                            "default": ["Q1", "Q2"]
                        },
                        "metric": {
                            "type": "string",
                            "description": "Financial metric to analyze (e.g., 'revenue', 'sales', 'profit')",
                            "default": "revenue"
                        }
                    },
                    "required": ["message_id", "file_data"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        logger = setup_logger(__name__)
        log_function_entry(logger, "execute", **kwargs)
        
        try:
            message_id = kwargs.get('message_id')
            file_data = kwargs.get('file_data')
            file_type = kwargs.get('file_type', 'excel')
            sheet_name = kwargs.get('sheet_name')
            quarters = kwargs.get('quarters', ['Q1', 'Q2'])
            metric = kwargs.get('metric', 'revenue').lower()
            
            df = self._load_data_from_bytes(file_data, file_type, sheet_name)
            df = self._clean_financial_data(df)
            detected_columns = self._detect_financial_columns(df)
            trend_data = self._extract_quarterly_trends(df, quarters, metric, detected_columns)
            chart_base64 = self._create_trend_chart(trend_data, metric, quarters, message_id)
            insights = self._generate_financial_insights(trend_data, metric, quarters)
            
            result = {
                "success": True,
                "data": {
                    "trend_data": trend_data,
                    "insights": insights,
                    "detected_columns": detected_columns,
                    "chart_saved": f"{message_id}.png" if chart_base64 else None
                }
            }
            
            log_function_exit(logger, "execute", result="analysis_completed")
            return result
            
        except Exception as e:
            log_exception(logger, e, "execute")
            result = {"success": False, "error": str(e)}
            log_function_exit(logger, "execute", result="analysis_failed")
            return result
    
    def _load_data_from_bytes(self, file_data: str, file_type: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        logger = setup_logger(__name__)
        
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
    
    def _detect_financial_columns(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        financial_keywords = {
            'revenue': ['revenue', 'sales', 'income', 'turnover'],
            'expenses': ['expenses', 'costs', 'expenditure', 'expense'],
            'profit': ['profit', 'earnings', 'net income'],
            'date': ['month', 'date', 'period', 'time'],
            'quarter': ['quarter', 'q1', 'q2', 'q3', 'q4']
        }
        
        detected_columns = {}
        for category, keywords in financial_keywords.items():
            detected_columns[category] = []
            for keyword in keywords:
                matching_cols = [col for col in df.columns if keyword in col.lower()]
                detected_columns[category].extend(matching_cols)
        
        return detected_columns
    
    def _clean_financial_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df_cleaned = df.copy()
        
        for col in df_cleaned.select_dtypes(include=['object']).columns:
            if col.lower() not in ['month', 'date', 'period', 'quarter']:
                df_cleaned[col] = df_cleaned[col].astype(str).str.replace('[$,]', '', regex=True)
                df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='ignore')
        
        return df_cleaned
    
    def _map_month_to_quarter(self, month_str: str) -> str:
        month_str = str(month_str).lower()
        
        if any(month in month_str for month in ['jan', 'feb', 'mar', '01', '02', '03']):
            return 'Q1'
        elif any(month in month_str for month in ['apr', 'may', 'jun', '04', '05', '06']):
            return 'Q2'
        elif any(month in month_str for month in ['jul', 'aug', 'sep', '07', '08', '09']):
            return 'Q3'
        elif any(month in month_str for month in ['oct', 'nov', 'dec', '10', '11', '12']):
            return 'Q4'
        else:
            return 'Unknown'
    
    def _extract_quarterly_trends(self, df: pd.DataFrame, quarters: List[str], metric: str, detected_columns: Dict[str, List[str]]) -> Dict[str, Any]:
        trend_data = {}
        
        metric_col = self._find_metric_column(df, metric, detected_columns)
        date_col = self._find_date_column(df, detected_columns)
        quarter_col = self._find_quarter_column(df, detected_columns)
        
        for quarter in quarters:
            trend_data[quarter] = {
                'values': [],
                'total': 0,
                'average': 0,
                'count': 0
            }
        
        if quarter_col:
            for quarter in quarters:
                quarter_rows = df[df[quarter_col].astype(str).str.contains(quarter, case=False, na=False)]
                if not quarter_rows.empty:
                    values = pd.to_numeric(quarter_rows[metric_col], errors='coerce').dropna().tolist()
                    self._populate_quarter_data(trend_data[quarter], values)
        else:
            for _, row in df.iterrows():
                month_str = str(row[date_col]) if date_col else ''
                quarter = self._map_month_to_quarter(month_str)
                if quarter in quarters:
                    try:
                        value = pd.to_numeric(row[metric_col], errors='coerce')
                        if not pd.isna(value):
                            trend_data[quarter]['values'].append(value)
                    except Exception:
                        continue
        
        for quarter in quarters:
            values = trend_data[quarter]['values']
            if values:
                trend_data[quarter]['total'] = sum(values)
                trend_data[quarter]['average'] = sum(values) / len(values)
                trend_data[quarter]['count'] = len(values)
        
        return trend_data
    
    def _find_metric_column(self, df: pd.DataFrame, metric: str, detected_columns: Dict[str, List[str]]) -> str:
        for col in df.columns:
            if metric.lower() in col.lower():
                return col
        
        if detected_columns.get(metric):
            return detected_columns[metric][0]
        
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            return numeric_cols[0]
        
        raise Exception(f"Could not find {metric} column in the data")
    
    def _find_date_column(self, df: pd.DataFrame, detected_columns: Dict[str, List[str]]) -> str:
        if detected_columns.get('date'):
            return detected_columns['date'][0]
        
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['month', 'date', 'period']):
                return col
        
        return df.columns[0]
    
    def _find_quarter_column(self, df: pd.DataFrame, detected_columns: Dict[str, List[str]]) -> Optional[str]:
        if detected_columns.get('quarter'):
            return detected_columns['quarter'][0]
        
        for col in df.columns:
            if 'quarter' in col.lower():
                return col
        
        return None
    
    def _populate_quarter_data(self, quarter_dict: Dict[str, Any], values: List[float]) -> None:
        if values:
            quarter_dict['values'] = values
            quarter_dict['total'] = sum(values)
            quarter_dict['average'] = sum(values) / len(values)
            quarter_dict['count'] = len(values)
    
    def _create_trend_chart(self, trend_data: Dict[str, Any], metric: str, quarters: List[str], message_id: str) -> str:
        try:
            plt.figure(figsize=(10, 6))
            
            quarter_names = []
            totals = []
            
            for quarter in quarters:
                if quarter in trend_data and trend_data[quarter]['total'] > 0:
                    quarter_names.append(quarter)
                    totals.append(trend_data[quarter]['total'])
            
            if not quarter_names:
                raise Exception("No data found for the specified quarters")
            
            plt.plot(quarter_names, totals, marker='o', linewidth=3, markersize=10, 
                    color='#2E86AB', markerfacecolor='#A23B72')
            plt.title(f'{metric.title()} Trends by Quarter', fontsize=16, fontweight='bold')
            plt.xlabel('Quarter')
            plt.ylabel(f'{metric.title()} Amount')
            plt.grid(True, alpha=0.3)
            
            ax = plt.gca()
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            for i, (quarter, total) in enumerate(zip(quarter_names, totals)):
                plt.annotate(f'${total:,.0f}', (i, total), textcoords="offset points", 
                            xytext=(0,15), ha='center', fontweight='bold')
            
            plt.tight_layout()
            
            # Save chart with message_id as filename
            os.makedirs("charts", exist_ok=True)
            plt.savefig(f"charts\{message_id}.png", format='png', dpi=300, bbox_inches='tight')
            
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            chart_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return chart_base64
        except Exception as e:
            raise Exception(f"Error creating trend chart: {str(e)}")
    
    def _generate_financial_insights(self, trend_data: Dict[str, Any], metric: str, quarters: List[str]) -> Dict[str, Any]:
        insights = {
            "growth_analysis": {},
            "performance_summary": {},
            "recommendations": []
        }
        
        valid_quarters = [q for q in quarters if trend_data.get(q, {}).get('total', 0) > 0]
        
        if len(valid_quarters) >= 2:
            first_quarter = valid_quarters[0]
            second_quarter = valid_quarters[1]
            
            q1_total = trend_data[first_quarter]['total']
            q2_total = trend_data[second_quarter]['total']
            
            if q1_total > 0:
                growth_rate = ((q2_total - q1_total) / q1_total) * 100
                insights["growth_analysis"] = {
                    f"{first_quarter}_total": q1_total,
                    f"{second_quarter}_total": q2_total,
                    "growth_rate": round(growth_rate, 2),
                    "growth_direction": "positive" if growth_rate > 0 else "negative" if growth_rate < 0 else "flat",
                    "absolute_change": q2_total - q1_total
                }
                
                insights["performance_summary"] = {
                    "best_quarter": first_quarter if q1_total > q2_total else second_quarter,
                    "total_revenue": q1_total + q2_total,
                    "average_quarterly": (q1_total + q2_total) / 2,
                    "quarters_analyzed": valid_quarters
                }
                
                self._add_recommendations(insights, growth_rate)
        
        return insights
    
    def _add_recommendations(self, insights: Dict[str, Any], growth_rate: float) -> None:
        if growth_rate > 15:
            insights["recommendations"].append("Exceptional growth momentum - consider aggressive expansion strategies")
        elif growth_rate > 5:
            insights["recommendations"].append("Strong growth trend - maintain current strategies and optimize operations")
        elif growth_rate > 0:
            insights["recommendations"].append("Positive growth trend - look for opportunities to accelerate growth")
        elif growth_rate > -5:
            insights["recommendations"].append("Stable performance - focus on efficiency improvements and new revenue streams")
        elif growth_rate > -15:
            insights["recommendations"].append("Declining trend - review pricing strategy and cost management")
        else:
            insights["recommendations"].append("Significant decline - urgent review of business strategy required")


async def main():
    logger = setup_logger(__name__)
    log_function_entry(logger, "main")
    
    try:
        import os
        logger.info("Initializing FinancialTrendAnalyzer")
        analyzer = FinancialTrendAnalyzer()

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

        # Execute analysis
        logger.info("Starting financial trend analysis")
        result = await analyzer.execute(
            file_data=file_base64,
            file_type=file_type,
            quarters=['Q1', 'Q2', "Q3"],
            metric='revenue'
        )

        # Display results
        if result.get("success"):
            logger.info("Financial trend analysis completed successfully")
            print(result)
            log_function_exit(logger, "main", result="analysis_completed")

    except Exception as e:
        log_exception(logger, e, "main")
        log_function_exit(logger, "main", result="analysis_failed")
        print(f"Error during analysis: {e}")
        raise
