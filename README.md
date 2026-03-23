# 📊 电商多智能体分析系统

基于 LangGraph 的多智能体电商数据分析系统，支持模拟数据、CSV上传、数据库连接，集成智谱 GLM-4 大模型。

## 🚀 功能特性

- **多智能体架构**: 4个专业Agent协作分析
  - 📥 数据采集Agent - 支持模拟数据/CSV/数据库
  - 👤 用户画像Agent - RFM分析 + LLM分群
  - 💰 销售分析Agent - 指标计算 + LLM洞察
  - 🎯 营销策略Agent - LLM生成策略

- **多种数据源**:
  - 模拟数据（100-1000条）
  - CSV/Excel文件上传
  - 数据库连接（MySQL/PostgreSQL/SQLite）

- **可视化界面**: Streamlit + Plotly 图表
- **报告导出**: JSON格式
- **历史记录**: 保存分析结果

## 🛠 技术栈

| 组件      | 技术                        |
| --------- | --------------------------- |
| Agent框架 | LangGraph                   |
| 大模型    | 智谱 GLM-4 Flash            |
| 后端      | FastAPI                     |
| 前端      | Streamlit                   |
| 数据库    | SQLite / MySQL / PostgreSQL |
| 可视化    | Plotly                      |

## 📦 安装

```bash
# 克隆项目
git clone https://github.com/你的用户名/ecommerce-multiagent.git
cd ecommerce-multiagent

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```
