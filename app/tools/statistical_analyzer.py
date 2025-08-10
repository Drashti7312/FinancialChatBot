import pandas as pd
import numpy as np
import base64
from io import BytesIO
from typing import Any, Dict, List
from .base_tool import BaseMCPTool
from scipy import stats

class StatisticalAnalyzer(BaseMCPTool):
    def __init__(self):
        super().__init__(
            name="statistical_analysis",
            description="Performs statistical analysis on CSV and Excel files"
        )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
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
                            "description": "Type of file being analyzed"
                        },
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific columns to analyze (optional, analyzes all numeric columns if not specified)",
                            "default": []
                        }
                    },
                    "required": ["file_data", "file_type"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            file_data = kwargs.get('file_data')
            file_type = kwargs.get('file_type', '').lower()
            columns = kwargs.get('columns', [])
            
            # Load data from file
            df = self._load_data_from_file(file_data, file_type)
            
            # Clean and prepare data
            df = self._clean_data(df)
            
            # Select columns for analysis
            numeric_columns = self._select_analysis_columns(df, columns)
            
            if not numeric_columns:
                return {
                    "success": False,
                    "error": "No numeric columns found for statistical analysis"
                }
            
            # Perform statistical analysis
            results = []
            for col in numeric_columns:
                series = df[col].dropna()
                if len(series) > 0:
                    col_stats = self._calculate_column_statistics(series, col)
                    results.append({col: col_stats})
            
            return {
                "success": True,
                "data": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _load_data_from_file(self, file_data: str, file_type: str) -> pd.DataFrame:
        """Load data from base64 encoded file"""
        try:
            if isinstance(file_data, bytes):
                file_bytes = file_data
            else:
                file_bytes = base64.b64decode(file_data)
                
            buffer = BytesIO(file_bytes)
            
            if file_type.lower() == 'csv':
                df = pd.read_csv(buffer)
            else:  # excel
                buffer.seek(0)
                engines = ['openpyxl', 'xlrd']
                df = None
                
                for engine in engines:
                    try:
                        buffer.seek(0)
                        df = pd.read_excel(buffer, engine=engine)
                        break
                    except Exception:
                        continue
                
                if df is None:
                    buffer.seek(0)
                    df = pd.read_excel(buffer)
            
            return df
            
        except Exception as e:
            raise Exception(f"Error loading {file_type} file: {str(e)}")
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare data for analysis"""
        # Remove completely empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Clean column names
        df.columns = df.columns.astype(str).str.strip()
        
        # Convert potential numeric columns
        for col in df.columns:
            if df[col].dtype == 'object':
                cleaned_series = df[col].astype(str).str.replace(r'[$,()%€£¥]', '', regex=True)
                cleaned_series = cleaned_series.str.replace('−', '-')
                cleaned_series = cleaned_series.str.replace(r'[^\d.-]', '', regex=True)
                
                numeric_series = pd.to_numeric(cleaned_series, errors='coerce')
                
                if numeric_series.notna().sum() / len(df) > 0.5:
                    df[col] = numeric_series
        
        return df
    
    def _select_analysis_columns(self, df: pd.DataFrame, specified_columns: List[str]) -> List[str]:
        """Select columns for statistical analysis"""
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if specified_columns:
            selected_columns = [col for col in specified_columns if col in numeric_columns]
        else:
            selected_columns = numeric_columns
        
        return selected_columns
    
    def _calculate_column_statistics(self, series: pd.Series, column_name: str) -> Dict[str, Any]:
        """Calculate statistics for a single column"""
        try:
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outliers = series[(series < lower_bound) | (series > upper_bound)]
            
            stats_dict = {
                "count": int(len(series)),
                "non_null_count": int(series.notna().sum()),
                "null_count": int(series.isna().sum()),
                "mean": float(series.mean()),
                "median": float(series.median()),
                "mode": float(series.mode().iloc[0]) if not series.mode().empty else None,
                "std": float(series.std()),
                "variance": float(series.var()),
                "min": float(series.min()),
                "max": float(series.max()),
                "range": float(series.max() - series.min()),
                "skewness": float(stats.skew(series, nan_policy='omit')),
                "kurtosis": float(stats.kurtosis(series, nan_policy='omit')),
                "q1": float(q1),
                "q2": float(series.quantile(0.5)),
                "q3": float(q3),
                "outlier_count": int(len(outliers)),
                "outlier_percentage": round((len(outliers) / len(series)) * 100, 2),
                "unique_values": int(series.nunique()),
                "unique_percentage": round((series.nunique() / len(series)) * 100, 2)
            }
            
            return stats_dict
            
        except Exception as e:
            return {"error": f"Failed to calculate statistics: {str(e)}"}


async def main():
    import os
    analyzer = StatisticalAnalyzer()

    uploaded_file_path = r"Documents\Financial_Q1_Q2_2023.xlsx"

    if not os.path.exists(uploaded_file_path):
        raise FileNotFoundError(f"File not found: {uploaded_file_path}")

    _, ext = os.path.splitext(uploaded_file_path)
    ext = ext.lower()
    if ext in [".xls", ".xlsx"]:
        file_type = "excel"
    elif ext == ".csv":
        file_type = "csv"
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    with open(uploaded_file_path, "rb") as f:
        file_bytes = f.read()
    file_base64 = base64.b64encode(file_bytes).decode()

    try:
        result = await analyzer.execute(
            file_data=file_base64,
            file_type=file_type
        )
        print(result)

    except Exception as e:
        print(f"Error during analysis: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())