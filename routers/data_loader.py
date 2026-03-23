"""数据加载器 - 支持CSV/Excel/数据库"""
import pandas as pd
from typing import Dict, Any
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import DB_TEMPLATES


def load_from_csv(uploaded_file) -> Dict:
    """从上传的CSV/Excel文件加载数据"""
    try:
        file_name = getattr(uploaded_file, 'name', '')
        
        if file_name.endswith('.csv'):
            orders = pd.read_csv(uploaded_file)
        elif file_name.endswith(('.xlsx', '.xls')):
            orders = pd.read_excel(uploaded_file)
        elif file_name.endswith('.json'):
            orders = pd.read_json(uploaded_file)
        else:
            orders = pd.read_csv(uploaded_file)
        
        # 标准化列名
        orders.columns = orders.columns.str.lower()
        
        # 验证必填列
        required_cols = ['user_id', 'amount']
        missing_cols = [col for col in required_cols if col not in orders.columns]
        if missing_cols:
            raise ValueError(f"缺少必填列: {', '.join(missing_cols)}")
        
        # 处理日期
        if 'order_date' not in orders.columns:
            orders['order_date'] = pd.Timestamp.now().date()
        orders['order_date'] = pd.to_datetime(orders['order_date'])
        
        # 填充可选列
        if 'channel' not in orders.columns:
            orders['channel'] = 'APP'
        if 'category' not in orders.columns:
            orders['category'] = '其他'
        if 'quantity' not in orders.columns:
            orders['quantity'] = 1
        
        # 构建用户数据
        users = pd.DataFrame({'user_id': orders['user_id'].unique()})
        users['age'] = 30
        users['gender'] = '未知'
        users['city'] = '未知'
        users['level'] = '普通'
        
        # 构建商品数据
        unique_categories = orders['category'].unique()
        products = pd.DataFrame({
            'product_id': range(1, len(unique_categories) + 1),
            'name': [f'商品_{i}' for i in range(1, len(unique_categories) + 1)],
            'category': unique_categories,
            'price': orders.groupby('category')['amount'].mean().reindex(unique_categories).fillna(100).values,
            'stock': 100
        })
        
        return {
            "status": "success",
            "data": {"orders": orders, "users": users, "products": products},
            "summary": {
                "orders_count": len(orders),
                "users_count": len(users),
                "products_count": len(products),
                "total_revenue": float(orders['amount'].sum()),
                "avg_order": float(orders['amount'].mean())
            }
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


def load_from_database(db_config: Dict) -> Dict:
    """从数据库加载数据"""
    try:
        db_type = db_config.get("type")
        template = DB_TEMPLATES.get(db_type, {})
        
        if db_type == "mysql":
            import pymysql
            conn = pymysql.connect(
                host=db_config.get("host", "localhost"),
                port=db_config.get("port", template.get("port", 3306)),
                user=db_config.get("user"),
                password=db_config.get("password"),
                database=db_config.get("database"),
                charset='utf8mb4'
            )
            query = db_config.get("query", template.get("query", "SELECT * FROM orders"))
            orders = pd.read_sql(query, conn)
            conn.close()
            
        elif db_type == "postgresql":
            import psycopg2
            conn = psycopg2.connect(
                host=db_config.get("host", "localhost"),
                port=db_config.get("port", template.get("port", 5432)),
                user=db_config.get("user"),
                password=db_config.get("password"),
                database=db_config.get("database")
            )
            query = db_config.get("query", template.get("query", "SELECT * FROM orders"))
            orders = pd.read_sql(query, conn)
            conn.close()
            
        elif db_type == "sqlite":
            import sqlite3
            conn = sqlite3.connect(db_config.get("path", "data/ecommerce.db"))
            query = db_config.get("query", template.get("query", "SELECT * FROM orders"))
            orders = pd.read_sql(query, conn)
            conn.close()
        else:
            return {"status": "error", "error": f"不支持的数据库类型: {db_type}"}
        
        if len(orders) == 0:
            return {"status": "error", "error": "数据库中没有数据"}
        
        orders.columns = orders.columns.str.lower()
        
        users = pd.DataFrame({'user_id': orders['user_id'].unique()})
        users['age'] = 30
        users['gender'] = '未知'
        users['city'] = '未知'
        
        products = pd.DataFrame({
            'product_id': range(1, 51),
            'name': [f'商品_{i}' for i in range(1, 51)],
            'category': orders['category'].unique()[:5] if 'category' in orders.columns else ['电子产品'],
            'price': 100,
            'stock': 100
        })
        
        return {
            "status": "success",
            "data": {"orders": orders, "users": users, "products": products},
            "summary": {
                "orders_count": len(orders),
                "users_count": len(users),
                "products_count": len(products),
                "total_revenue": float(orders['amount'].sum()) if 'amount' in orders.columns else 0
            }
        }
        
    except ImportError as e:
        return {"status": "error", "error": f"缺少数据库驱动: {e}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}