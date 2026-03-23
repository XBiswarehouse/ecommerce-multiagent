"""销售分析Agent - 简化版，只算指标"""
import pandas as pd
import json
import re
from typing import Dict, Any, List
from .base import BaseAgent


class SalesAnalyzerAgent(BaseAgent):
    """销售分析Agent - 只计算指标，不调LLM"""
    
    def __init__(self):
        super().__init__(name="sales_analyzer", role="销售分析专家")
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行销售分析（快速版本）"""
        self.logger.info("开始销售分析...")
        
        orders = task.get("orders_data")
        
        if orders is None or len(orders) == 0:
            return {"agent": self.name, "status": "error", "message": "缺少订单数据"}
        
        # 计算指标
        metrics = self._calculate_metrics(orders)
        channel_analysis = self._analyze_channels(orders)
        category_analysis = self._analyze_categories(orders)
        trends = self._analyze_trends(orders)
        
        # 准备数据摘要
        data_summary = self._prepare_data_summary(metrics, channel_analysis, category_analysis, trends)
        
        self.logger.info(f"销售分析完成")
        
        return {
            "agent": self.name,
            "status": "success",
            "metrics": metrics,
            "channel_analysis": channel_analysis,
            "category_analysis": category_analysis,
            "trends": trends,
            "data_summary": data_summary  # 传递给营销Agent
        }
    
    def _calculate_metrics(self, orders: pd.DataFrame) -> Dict:
        """计算核心指标"""
        total_revenue = orders['amount'].sum()
        total_orders = len(orders)
        
        return {
            "total_revenue": round(float(total_revenue), 2),
            "total_orders": int(total_orders),
            "avg_order_value": round(float(total_revenue / total_orders), 2) if total_orders > 0 else 0,
            "unique_customers": int(orders['user_id'].nunique()),
            "total_quantity": int(orders['quantity'].sum())
        }
    
    def _analyze_channels(self, orders: pd.DataFrame) -> List[Dict]:
        """渠道分析"""
        channel_stats = orders.groupby('channel').agg({
            'amount': 'sum',
            'order_id': 'count'
        }).reset_index()
        channel_stats.columns = ['channel', 'revenue', 'orders']
        
        total = channel_stats['revenue'].sum()
        
        result = []
        for _, row in channel_stats.iterrows():
            result.append({
                "channel": row['channel'],
                "revenue": round(float(row['revenue']), 2),
                "percentage": round(row['revenue'] / total * 100, 1) if total > 0 else 0,
                "orders": int(row['orders'])
            })
        
        return sorted(result, key=lambda x: x['revenue'], reverse=True)
    
    def _analyze_categories(self, orders: pd.DataFrame) -> List[Dict]:
        """品类分析"""
        category_stats = orders.groupby('category').agg({
            'amount': 'sum',
            'order_id': 'count'
        }).reset_index()
        category_stats.columns = ['category', 'revenue', 'orders']
        
        total = category_stats['revenue'].sum()
        
        result = []
        for _, row in category_stats.iterrows():
            result.append({
                "category": row['category'],
                "revenue": round(float(row['revenue']), 2),
                "percentage": round(row['revenue'] / total * 100, 1) if total > 0 else 0,
                "orders": int(row['orders'])
            })
        
        return sorted(result, key=lambda x: x['revenue'], reverse=True)
    
    def _analyze_trends(self, orders: pd.DataFrame) -> Dict:
        """趋势分析"""
        orders['date'] = pd.to_datetime(orders['order_date']).dt.date
        daily = orders.groupby('date')['amount'].sum().reset_index()
        daily.columns = ['date', 'revenue']
        
        peak = daily.loc[daily['revenue'].idxmax()] if len(daily) > 0 else None
        valley = daily.loc[daily['revenue'].idxmin()] if len(daily) > 0 else None
        
        return {
            "peak_day": {"date": str(peak['date']), "revenue": float(peak['revenue'])} if peak is not None else None,
            "valley_day": {"date": str(valley['date']), "revenue": float(valley['revenue'])} if valley is not None else None
        }
    
    def _prepare_data_summary(self, metrics: Dict, channel_analysis: List, 
                               category_analysis: List, trends: Dict) -> str:
        """准备数据摘要"""
        summary = f"总营收: {metrics['total_revenue']:.0f}元\n"
        summary += f"订单数: {metrics['total_orders']}单\n"
        summary += f"客单价: {metrics['avg_order_value']:.0f}元\n"
        
        if channel_analysis:
            top_channel = channel_analysis[0]
            summary += f"主力渠道: {top_channel['channel']} ({top_channel['percentage']}%)\n"
        
        if category_analysis:
            top_category = category_analysis[0]
            summary += f"主力品类: {top_category['category']} ({top_category['percentage']}%)\n"
        
        return summary