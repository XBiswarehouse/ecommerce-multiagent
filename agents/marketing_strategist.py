"""营销策略Agent - 唯一调用LLM的Agent"""
import json
import re
from typing import Dict, Any, List
from .base import BaseAgent


class MarketingStrategistAgent(BaseAgent):
    """营销策略Agent - 只在这里调用LLM生成完整报告"""
    
    def __init__(self):
        super().__init__(name="marketing_strategist", role="营销策略专家")
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行营销策略生成 - 一次LLM调用生成完整报告"""
        self.logger.info("开始生成营销策略...")
        
        # 获取数据摘要
        user_summary = task.get("user_data_summary", "")
        sales_summary = task.get("sales_data_summary", "")
        
        # 使用提示词模板构建输入（从 prompts/ 加载）
        user_message = self._build_user_message(user_summary, sales_summary)
        
        # 一次LLM调用生成完整策略
        strategy_result = self._generate_strategy_with_llm(user_message)
        
        self.logger.info(f"营销策略生成完成")
        
        return {
            "agent": self.name,
            "status": "success",
            "overall_strategy": strategy_result.get("overall_strategy", ""),
            "action_plan": strategy_result.get("action_plan", []),
            "expected_impact": strategy_result.get("expected_impact", "")
        }
    
    def _build_user_message(self, user_summary: str, sales_summary: str) -> str:
        """使用提示词模板构建用户消息"""
        # 从 base 类加载的 prompt 中提取模板
        # 这里简单拼接，也可以从 yaml 读取模板
        return f"""
请根据以下数据，制定营销策略：

【用户数据】
{user_summary}

【销售数据】
{sales_summary}

请以JSON格式输出营销策略。
"""
    
    def _generate_strategy_with_llm(self, user_message: str) -> Dict:
        """用LLM生成营销策略"""
        
        # 直接使用 base 类的 _call_llm 方法
        # base 类已经处理了 system_prompt 的加载
        response = self._call_llm(user_message, temperature=0.7, use_cache=True)
        
        # 如果LLM失败，返回默认策略
        if "Mock" in response or "错误" in response or not self.llm:
            return self._default_strategy()
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return self._default_strategy()
        except Exception as e:
            self.logger.error(f"解析LLM响应失败: {e}")
            return self._default_strategy()
    
    def _default_strategy(self) -> Dict:
        """默认营销策略"""
        return {
            "overall_strategy": "维护高价值用户，提升用户活跃度",
            "action_plan": [
                {"target": "高价值用户", "action": "专属VIP权益", "channel": "APP推送", "priority": "高"},
                {"target": "流失风险用户", "action": "发送召回优惠券", "channel": "短信", "priority": "高"},
                {"target": "潜力用户", "action": "推送个性化推荐", "channel": "小程序", "priority": "中"}
            ],
            "expected_impact": "预计提升15%复购率"
        }