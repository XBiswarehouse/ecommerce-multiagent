"""Streamlit可视化界面 - 完整功能版"""
import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from routers.workflow import run_analysis

st.set_page_config(page_title="电商多智能体分析系统", page_icon="📊", layout="wide")

st.title("📊 电商多智能体分析系统")
st.markdown("基于 LangGraph 的多智能体协作分析平台 | 支持模拟数据/CSV/数据库")

with st.sidebar:
    st.header("⚙️ 配置")
    
    # 数据源选择
    data_source = st.selectbox(
        "数据来源",
        ["模拟数据", "上传CSV文件", "数据库连接"],
        help="选择数据来源方式"
    )
    
    uploaded_file = None
    db_config = None
    data_size = 500
    
    if data_source == "模拟数据":
        data_size = st.slider("数据量（订单数）", min_value=100, max_value=1000, value=500, step=100)
    
    elif data_source == "上传CSV文件":
        uploaded_file = st.file_uploader("选择CSV文件", type=["csv"], help="需包含: user_id, amount, order_date")
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.success(f"✅ 上传成功: {len(df)} 条记录")
            except Exception as e:
                st.error(f"读取失败: {e}")
                uploaded_file = None
    
    elif data_source == "数据库连接":
        st.markdown("### 数据库配置")
        db_type = st.selectbox("数据库类型", ["SQLite", "MySQL", "PostgreSQL"])
        
        if db_type == "SQLite":
            db_path = st.text_input("数据库文件路径", "data/ecommerce.db")
            db_config = {"type": "sqlite", "path": db_path}
        else:
            col1, col2 = st.columns(2)
            with col1:
                db_host = st.text_input("主机", "localhost")
                db_user = st.text_input("用户名")
            with col2:
                db_port = st.number_input("端口", value=3306 if db_type == "MySQL" else 5432)
                db_password = st.text_input("密码", type="password")
            db_name = st.text_input("数据库名")
            db_table = st.text_input("表名", "orders")
            
            if db_user and db_name:
                db_config = {
                    "type": db_type.lower(),
                    "host": db_host,
                    "port": db_port,
                    "user": db_user,
                    "password": db_password,
                    "database": db_name,
                    "query": f"SELECT * FROM {db_table}"
                }
                st.success("✅ 配置已保存")
    
    start = st.button("🚀 开始分析", type="primary", use_container_width=True)

if start:
    # 验证
    if data_source == "上传CSV文件" and uploaded_file is None:
        st.error("请先上传CSV文件")
        st.stop()
    if data_source == "数据库连接" and db_config is None:
        st.error("请先配置数据库连接")
        st.stop()
    
    with st.spinner("正在执行多智能体分析..."):
        result = run_analysis(
            data_size=data_size,
            uploaded_file=uploaded_file,
            db_config=db_config
        )
    
    if result.get("status") == "error":
        st.error("分析失败")
        with st.expander("错误详情"):
            st.json(result.get("errors", []))
    else:
        # 数据采集
        st.subheader("📥 数据采集")
        collect = result.get("data_collection", {})
        if collect.get("summary"):
            summary = collect["summary"]
            col1, col2, col3 = st.columns(3)
            col1.metric("订单数", summary.get("orders_count", 0))
            col2.metric("用户数", summary.get("users_count", 0))
            col3.metric("商品数", summary.get("products_count", 0))
        
        # 用户画像
        st.subheader("👤 用户画像")
        profile = result.get("user_profile", {})
        segments = profile.get("segments", [])
        if segments:
            seg_df = pd.DataFrame(segments)
            fig = px.pie(seg_df, values='count', names='name', title='用户分群', hole=0.3)
            st.plotly_chart(fig)
            if profile.get("insights"):
                st.info(f"💡 {profile['insights']}")
        
        # 销售分析
        st.subheader("💰 销售分析")
        sales = result.get("sales_analysis", {})
        metrics = sales.get("metrics", {})
        if metrics:
            col1, col2, col3 = st.columns(3)
            col1.metric("总营收", f"¥{metrics.get('total_revenue', 0):,.0f}")
            col2.metric("总订单数", f"{metrics.get('total_orders', 0)}")
            col3.metric("客单价", f"¥{metrics.get('avg_order_value', 0):,.0f}")
            
            channel = sales.get("channel_analysis", [])
            if channel:
                st.write("**渠道分布**")
                channel_df = pd.DataFrame(channel)
                fig = px.bar(channel_df, x='channel', y='revenue', title='各渠道营收', text='percentage')
                fig.update_traces(texttemplate='%{text}%', textposition='outside')
                st.plotly_chart(fig)
            
            category = sales.get("category_analysis", [])
            if category:
                st.write("**品类分布**")
                category_df = pd.DataFrame(category)
                fig = px.pie(category_df, values='revenue', names='category', title='品类占比', hole=0.3)
                st.plotly_chart(fig)
            
            if sales.get("insights"):
                st.markdown(f'💡 {sales["insights"]}')
        
        # 营销策略
        st.subheader("🎯 营销策略")
        marketing = result.get("marketing_strategy", {})
        if marketing.get("overall_strategy"):
            st.success(f"🎯 {marketing['overall_strategy']}")
            
            action_plan = marketing.get("action_plan", [])
            if action_plan:
                st.write("**执行计划**")
                for plan in action_plan[:3]:
                    st.markdown(f"- **{plan.get('target', '')}**: {plan.get('action', '')} ({plan.get('channel', '')})")
            
            if marketing.get("expected_impact"):
                st.info(f"📈 {marketing['expected_impact']}")
        
        # 导出按钮
        st.markdown("---")
        if st.button("📥 导出JSON报告"):
            import json
            report = {
                "time": datetime.now().isoformat(),
                "data_source": data_source,
                "result": result
            }
            json_str = json.dumps(report, ensure_ascii=False, indent=2, default=str)
            st.download_button(
                label="下载报告",
                data=json_str,
                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        st.success("✅ 分析完成！")
else:
    st.info("👈 左侧选择数据来源，点击「开始分析」")