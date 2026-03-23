"""条件判断函数"""
from typing import Dict, Any


def has_data_error(state: Dict[str, Any]) -> str:
    """检查是否有数据错误"""
    errors = state.get("errors", [])
    if errors:
        return "error"
    return "continue"


def should_skip_marketing(state: Dict[str, Any]) -> str:
    """检查是否跳过营销策略"""
    user_profile = state.get("user_profile")
    sales_analysis = state.get("sales_analysis")
    
    if user_profile and sales_analysis:
        return "continue"
    return "skip"


def analysis_complete(state: Dict[str, Any]) -> bool:
    """检查分析是否完成"""
    return state.get("status") == "completed"