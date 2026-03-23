"""用户画像Agent - 简化版，只做数据准备"""
import pandas as pd
import json
import re
from typing import Dict, Any, List
from .base import BaseAgent


class UserProfilerAgent(BaseAgent):
    """用户画像Agent - 数据准备 + 规则分群"""
    
    def __init__(self):
        super().__init__(name="user_profiler", role="用户画像专家")
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行用户画像分析（快速版本，不调LLM）"""
        self.logger.info("开始用户画像分析...")
        
        orders = task.get("orders_data")
        users = task.get("users_data")
        
        if orders is None or len(orders) == 0:
            return {"agent": self.name, "status": "error", "message": "缺少订单数据"}
        
        # 计算RFM
        rfm = self._calculate_rfm(orders)
        
        # 规则分群（快速）
        segments = self._segment_users(rfm)
        
        # 准备数据摘要（供营销Agent使用）
        data_summary = self._prepare_data_summary(rfm, users, segments)
        
        self.logger.info(f"用户画像完成: {len(rfm)}个用户")
        
        return {
            "agent": self.name,
            "status": "success",
            "segments": segments,
            "insights": self._generate_insight(segments),
            "data_summary": data_summary  # 传递给营销Agent
        }
    
    def _calculate_rfm(self, orders: pd.DataFrame) -> pd.DataFrame:
        """计算RFM指标"""
        last_date = orders['order_date'].max()
        
        recency = orders.groupby('user_id')['order_date'].max().apply(
            lambda x: (last_date - x).days
        ).reset_index()
        recency.columns = ['user_id', 'recency']
        
        freq_amount = orders.groupby('user_id').agg({
            'order_id': 'count',
            'amount': 'sum'
        }).reset_index()
        freq_amount.columns = ['user_id', 'frequency', 'monetary']
        
        rfm = recency.merge(freq_amount, on='user_id', how='left')
        rfm = rfm.fillna({'frequency': 0, 'monetary': 0})
        
        return rfm
    
    def _segment_users(self, rfm: pd.DataFrame) -> List[Dict]:
        """快速规则分群"""
        if len(rfm) == 0:
            return []
        
        # 打分
        rfm['r_score'] = pd.cut(rfm['recency'], 4, labels=['4', '3', '2', '1'])
        rfm['f_score'] = pd.cut(rfm['frequency'], 4, labels=['1', '2', '3', '4'])
        
        # 分群
        segments = []
        for _, row in rfm.iterrows():
            r = int(row['r_score'])
            f = int(row['f_score'])
            
            if r >= 3 and f >= 3:
                seg = '高价值用户'
            elif r >= 3 and f <= 2:
                seg = '潜力用户'
            elif r <= 2 and f >= 3:
                seg = '忠诚用户'
            else:
                seg = '流失风险用户'
            segments.append(seg)
        
        rfm['segment'] = segments
        
        # 统计
        stats = rfm['segment'].value_counts().to_dict()
        
        return [
            {"name": name, "count": count, "percentage": round(count / len(rfm) * 100, 1)}
            for name, count in stats.items()
        ]
    
    def _generate_insight(self, segments: List[Dict]) -> str:
        """快速生成洞察"""
        if not segments:
            return "暂无数据"
        top = max(segments, key=lambda x: x['count'])
        return f"{top['name']}占比{top['percentage']}%，是主要用户群体"
    
    def _prepare_data_summary(self, rfm: pd.DataFrame, users: pd.DataFrame, segments: List[Dict]) -> str:
        """准备数据摘要供营销Agent使用"""
        summary = f"总用户数: {len(rfm)}\n"
        summary += f"平均消费: {rfm['monetary'].mean():.0f}元\n"
        summary += f"平均频次: {rfm['frequency'].mean():.1f}次\n"
        summary += f"用户分群: "
        for seg in segments:
            summary += f"{seg['name']}{seg['percentage']}% "
        return summary