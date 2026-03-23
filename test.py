"""测试模拟数据"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from routers.workflow import run_analysis

print("测试模拟数据...")
result = run_analysis(data_size=100, uploaded_file=None, db_config=None)

print("状态:", result.get("status"))
print("数据采集:", result.get("data_collection") is not None)
if result.get("data_collection"):
    print("订单数:", result.get("data_collection").get("summary", {}).get("orders_count", 0))
print("错误:", result.get("errors", []))