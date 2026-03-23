"""数据采集Agent - 生成模拟电商数据"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any
from .base import BaseAgent


class DataCollectorAgent(BaseAgent):
    """数据采集Agent"""
    
    def __init__(self):
        super().__init__(name="data_collector", role="数据采集专家")
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据采集"""
        self.logger.info("开始采集数据...")
        
        data_size = task.get("data_size", 500)
        
        orders = self._generate_orders(data_size)
        users = self._generate_users(data_size // 5)
        products = self._generate_products(50)
        
        self.logger.info(f"采集完成: {len(orders)}条订单, {len(users)}个用户")
        
        return {
            "agent": self.name,
            "status": "success",
            "data": {
                "orders": orders,
                "users": users,
                "products": products
            },
            "summary": {
                "orders_count": len(orders),
                "users_count": len(users),
                "products_count": len(products)
            }
        }
    
    def _generate_orders(self, n: int) -> pd.DataFrame:
        """生成订单数据"""
        np.random.seed(42)
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 3, 31)
        date_range = (end_date - start_date).days
        
        dates = [start_date + timedelta(days=np.random.randint(0, date_range)) 
                 for _ in range(n)]
        dates.sort()
        
        return pd.DataFrame({
            'order_id': range(1001, 1001 + n),
            'user_id': np.random.randint(1, n // 5 + 1, n),
            'order_date': dates,
            'amount': np.random.uniform(50, 2000, n).round(2),
            'quantity': np.random.randint(1, 5, n),
            'status': np.random.choice(['已完成', '已发货', '处理中'], n, p=[0.7, 0.2, 0.1]),
            'channel': np.random.choice(['APP', '小程序', 'PC'], n, p=[0.6, 0.3, 0.1]),
            'category': np.random.choice(['电子产品', '服装', '家居', '美妆', '食品'], n)
        })
    
    def _generate_users(self, n: int) -> pd.DataFrame:
        """生成用户数据"""
        np.random.seed(43)
        return pd.DataFrame({
            'user_id': range(1, n + 1),
            'age': np.random.randint(18, 65, n),
            'gender': np.random.choice(['男', '女'], n, p=[0.48, 0.52]),
            'city': np.random.choice(['北京', '上海', '广州', '深圳', '杭州'], n),
            'level': np.random.choice(['普通', '白银', '黄金'], n, p=[0.6, 0.3, 0.1])
        })
    
    def _generate_products(self, n: int) -> pd.DataFrame:
        """生成商品数据"""
        np.random.seed(44)
        categories = ['电子产品', '服装', '家居', '美妆', '食品']
        return pd.DataFrame({
            'product_id': range(1, n + 1),
            'name': [f'商品_{i}' for i in range(1, n + 1)],
            'category': np.random.choice(categories, n),
            'price': np.random.uniform(29, 2999, n).round(2),
            'stock': np.random.randint(0, 500, n)
        })