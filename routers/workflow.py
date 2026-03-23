"""工作流定义 - 编排Agent执行顺序"""
from typing import Dict, Any, TypedDict, List
from langgraph.graph import StateGraph, END
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from agents import (
    DataCollectorAgent,
    UserProfilerAgent,
    SalesAnalyzerAgent,
    MarketingStrategistAgent
)
from .data_loader import load_from_csv, load_from_database


class AnalysisState(TypedDict):
    """工作流状态"""
    data_size: int
    uploaded_file: Any
    db_config: Any
    raw_data: Any
    user_profile: Any
    sales_analysis: Any
    marketing_strategy: Any
    errors: List[str]
    status: str
    start_time: float


# 初始化Agent
_collector = DataCollectorAgent()
_profiler = UserProfilerAgent()
_sales = SalesAnalyzerAgent()
_marketing = MarketingStrategistAgent()


def collect_node(state: AnalysisState) -> Dict:
    """数据采集节点"""
    print("[工作流] 开始数据采集...")
    
    uploaded_file = state.get("uploaded_file")
    db_config = state.get("db_config")
    
    if uploaded_file is not None:
        result = load_from_csv(uploaded_file)
    elif db_config is not None:
        result = load_from_database(db_config)
    else:
        result = _collector.execute({"data_size": state.get("data_size", 500)})
    
    if result.get("status") != "success":
        print(f"[工作流] 数据采集失败: {result.get('error')}")
    
    return {"raw_data": result}


def profile_node(state: AnalysisState) -> Dict:
    """用户画像节点"""
    print("[工作流] 执行用户画像...")
    
    raw = state.get("raw_data", {})
    orders = raw.get("data", {}).get("orders")
    users = raw.get("data", {}).get("users")
    
    if orders is None or len(orders) == 0:
        return {"errors": state.get("errors", []) + ["缺少订单数据"]}
    
    result = _profiler.execute({"orders_data": orders, "users_data": users})
    return {"user_profile": result}


def sales_node(state: AnalysisState) -> Dict:
    """销售分析节点"""
    print("[工作流] 执行销售分析...")
    
    raw = state.get("raw_data", {})
    orders = raw.get("data", {}).get("orders")
    
    if orders is None or len(orders) == 0:
        return {"errors": state.get("errors", []) + ["缺少订单数据"]}
    
    result = _sales.execute({"orders_data": orders})
    return {"sales_analysis": result}


def marketing_node(state: AnalysisState) -> Dict:
    """营销策略节点"""
    print("[工作流] 生成营销策略...")
    
    user_profile = state.get("user_profile", {})
    sales_analysis = state.get("sales_analysis", {})
    
    result = _marketing.execute({
        "user_data_summary": user_profile.get("data_summary", ""),
        "sales_data_summary": sales_analysis.get("data_summary", "")
    })
    
    elapsed = time.time() - state.get("start_time", time.time())
    print(f"[工作流] 完成，耗时: {elapsed:.2f}s")
    
    return {"marketing_strategy": result, "status": "completed"}


def create_workflow():
    """创建工作流图"""
    workflow = StateGraph(AnalysisState)
    
    workflow.add_node("collect", collect_node)
    workflow.add_node("profile", profile_node)
    workflow.add_node("sales", sales_node)
    workflow.add_node("marketing", marketing_node)
    
    workflow.set_entry_point("collect")
    
    # 并行执行
    workflow.add_edge("collect", "profile")
    workflow.add_edge("collect", "sales")
    workflow.add_edge("profile", "marketing")
    workflow.add_edge("sales", "marketing")
    workflow.add_edge("marketing", END)
    
    return workflow.compile()


def run_analysis(data_size: int = 500, uploaded_file=None, db_config=None) -> Dict[str, Any]:
    """执行分析"""
    try:
        print("=" * 60)
        print("开始多智能体分析")
        source = "文件" if uploaded_file else "数据库" if db_config else "模拟"
        print(f"数据源: {source}")
        print("=" * 60)
        
        workflow = create_workflow()
        
        initial_state: AnalysisState = {
            "data_size": data_size,
            "uploaded_file": uploaded_file,
            "db_config": db_config,
            "raw_data": None,
            "user_profile": None,
            "sales_analysis": None,
            "marketing_strategy": None,
            "errors": [],
            "status": "running",
            "start_time": time.time()
        }
        
        final_state = workflow.invoke(initial_state)
        
        # 检查错误
        if final_state.get("raw_data", {}).get("status") == "error":
            return {
                "status": "error",
                "data_collection": None,
                "user_profile": None,
                "sales_analysis": None,
                "marketing_strategy": None,
                "errors": [final_state.get("raw_data", {}).get("error", "数据加载失败")]
            }
        
        user_profile = final_state.get("user_profile", {})
        sales_analysis = final_state.get("sales_analysis", {})
        marketing_strategy = final_state.get("marketing_strategy", {})
        
        return {
            "status": final_state.get("status", "success"),
            "data_collection": final_state.get("raw_data"),
            "user_profile": {
                "segments": user_profile.get("segments", []),
                "insights": user_profile.get("insights", ""),
                "recommendations": user_profile.get("recommendations", [])
            },
            "sales_analysis": {
                "metrics": sales_analysis.get("metrics", {}),
                "channel_analysis": sales_analysis.get("channel_analysis", []),
                "category_analysis": sales_analysis.get("category_analysis", []),
                "trends": sales_analysis.get("trends", {}),
                "insights": sales_analysis.get("insights", ""),
                "problems": sales_analysis.get("problems", []),
                "opportunities": sales_analysis.get("opportunities", [])
            },
            "marketing_strategy": marketing_strategy,
            "errors": final_state.get("errors", [])
        }
        
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "data_collection": None,
            "user_profile": None,
            "sales_analysis": None,
            "marketing_strategy": None,
            "errors": [str(e), traceback.format_exc()]
        }