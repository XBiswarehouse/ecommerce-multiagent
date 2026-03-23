"""LangGraph工作流定义 - 优化版"""
from typing import Dict, Any, Optional, TypedDict, List
from langgraph.graph import StateGraph, END
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from agents import (
    DataCollectorAgent,
    UserProfilerAgent,
    SalesAnalyzerAgent,
    MarketingStrategistAgent
)


class AnalysisState(TypedDict):
    """工作流状态"""
    data_size: int
    raw_data: Optional[Dict]
    user_profile: Optional[Dict]
    sales_analysis: Optional[Dict]
    marketing_strategy: Optional[Dict]
    errors: List[str]
    status: str


# 初始化Agent
_collector = DataCollectorAgent()
_profiler = UserProfilerAgent()
_sales = SalesAnalyzerAgent()
_marketing = MarketingStrategistAgent()


def collect_node(state: AnalysisState) -> Dict:
    """数据采集节点"""
    result = _collector.execute({"data_size": state.get("data_size", 500)})
    return {"raw_data": result}


def profile_node(state: AnalysisState) -> Dict:
    """用户画像节点"""
    raw = state.get("raw_data", {})
    orders = raw.get("data", {}).get("orders")
    users = raw.get("data", {}).get("users")
    result = _profiler.execute({"orders_data": orders, "users_data": users})
    return {"user_profile": result}


def sales_node(state: AnalysisState) -> Dict:
    """销售分析节点"""
    raw = state.get("raw_data", {})
    orders = raw.get("data", {}).get("orders")
    result = _sales.execute({"orders_data": orders})
    return {"sales_analysis": result}


def marketing_node(state: AnalysisState) -> Dict:
    """营销策略节点 - 唯一调用LLM的地方"""
    user_profile = state.get("user_profile", {})
    sales_analysis = state.get("sales_analysis", {})
    
    # 传递数据摘要，让营销Agent自己调LLM
    result = _marketing.execute({
        "user_data_summary": user_profile.get("data_summary", ""),
        "sales_data_summary": sales_analysis.get("data_summary", "")
    })
    
    return {"marketing_strategy": result, "status": "completed"}


def create_workflow():
    """创建工作流图 - 并行执行profile和sales"""
    workflow = StateGraph(AnalysisState)
    
    workflow.add_node("collect", collect_node)
    workflow.add_node("profile", profile_node)
    workflow.add_node("sales", sales_node)
    workflow.add_node("marketing", marketing_node)
    
    workflow.set_entry_point("collect")
    
    # 并行执行 profile 和 sales
    workflow.add_edge("collect", "profile")
    workflow.add_edge("collect", "sales")
    
    # 都完成后执行 marketing
    workflow.add_edge("profile", "marketing")
    workflow.add_edge("sales", "marketing")
    workflow.add_edge("marketing", END)
    
    return workflow.compile()


def run_analysis(data_size: int = 500) -> Dict[str, Any]:
    """执行分析"""
    try:
        app = create_workflow()
        
        initial_state: AnalysisState = {
            "data_size": data_size,
            "raw_data": None,
            "user_profile": None,
            "sales_analysis": None,
            "marketing_strategy": None,
            "errors": [],
            "status": "running"
        }
        
        final_state = app.invoke(initial_state)
        
        # 提取结果
        user_profile = final_state.get("user_profile", {})
        sales_analysis = final_state.get("sales_analysis", {})
        marketing_strategy = final_state.get("marketing_strategy", {})
        
        return {
            "status": final_state.get("status", "success"),
            "data_collection": final_state.get("raw_data"),
            "user_profile": {
                "segments": user_profile.get("segments", []),
                "insights": user_profile.get("insights", "")
            },
            "sales_analysis": {
                "metrics": sales_analysis.get("metrics", {}),
                "channel_analysis": sales_analysis.get("channel_analysis", []),
                "category_analysis": sales_analysis.get("category_analysis", []),
                "insights": ""  # 不单独生成洞察
            },
            "marketing_strategy": marketing_strategy,
            "errors": final_state.get("errors", [])
        }
        
    except Exception as e:
        return {
            "status": "error",
            "data_collection": None,
            "user_profile": None,
            "sales_analysis": None,
            "marketing_strategy": None,
            "errors": [str(e)]
        }