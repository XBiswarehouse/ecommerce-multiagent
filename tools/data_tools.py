"""数据处理工具函数"""
import pandas as pd
from typing import Dict, Any, List


def dataframe_to_dict(df: pd.DataFrame) -> List[Dict]:
    """将DataFrame转换为字典列表"""
    if df is None or len(df) == 0:
        return []
    return df.to_dict('records')


def get_data_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """获取数据摘要"""
    if df is None or len(df) == 0:
        return {"rows": 0, "columns": []}
    
    return {
        "rows": len(df),
        "columns": df.columns.tolist(),
        "null_counts": df.isnull().sum().to_dict()
    }