# ===== Streamlit Web 可视化面板 =====
# 提供达人数据的交互式浏览、筛选、详情查看和导出功能

import os                                  # 操作系统模块
import sys                                 # 系统模块
import streamlit as st                     # Streamlit Web 框架
import pandas as pd                        # 数据处理
import plotly.graph_objects as go           # Plotly 图表（雷达图）
from datetime import datetime              # 日期时间

# 将项目根目录添加到 Python 路径（确保能导入其他模块）
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.database import Database       # 数据库操作类
from export.exporter import Exporter       # 数据导出器


def get_db():
    """
    获取数据库实例（单例模式，缓存在 Streamlit session 中）。
    返回:
        Database 实例
    """
    # 使用 session_state 缓存数据库连接
    if "db" not in st.session_state:
        st.session_state.db = Database()  # 首次访问时创建
    return st.session_state.db


def main():
    """
    Streamlit 应用主函数。
    定义页面布局、侧边栏导航和各页面内容。
    """
    # ----- 页面配置 -----
    st.set_page_config(
        page_title="小红书达人评估面板",       # 浏览器标签页标题
        page_icon="📊",                       # 页面图标
        layout="wide",                        # 宽屏布局
        initial_sidebar_state="expanded"       # 默认展开侧边栏
    )

    # ----- 自定义 CSS 样式 -----
    st.markdown("""
    <style>
        /* 主标题样式 */
        .main-title {
            font-size: 2rem;              /* 标题字号 */
            font-weight: bold;            /* 加粗 */
            color: #FF2442;               /* 小红书品牌红 */
            margin-bottom: 0.5rem;        /* 底部间距 */
        }
        /* 等级标签样式 */
        .grade-s { color: #FF2442; font-weight: bold; font-size: 1.5rem; }  /* S级：红色 */
        .grade-a { color: #FF6B35; font-weight: bold; font-size: 1.5rem; }  /* A级：橙色 */
        .grade-b { color: #FFA500; font-weight: bold; font-size: 1.5rem; }  /* B级：黄色 */
        .grade-c { color: #4CAF50; font-weight: bold; font-size: 1.5rem; }  /* C级：绿色 */
        .grade-d { color: #9E9E9E; font-weight: bold; font-size: 1.5rem; }  /* D级：灰色 */
        /* 指标卡片样式 */
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);  /* 渐变背景 */
            border-radius: 12px;          /* 圆角 */
            padding: 1.2rem;             /* 内边距 */
            color: white;                 /* 白色文字 */
            text-align: center;           /* 居中 */
            margin-bottom: 1rem;          /* 底部间距 */
        }
        .metric-value {
            font-size: 2rem;              /* 数值字号 */
            font-weight: bold;            /* 加粗 */
        }
        .metric-label {
            font-size: 0.9rem;            /* 标签字号 */
            opacity: 0.9;                 /* 略透明 */
        }
    </style>
    """, unsafe_allow_html=True)

    # ----- 侧边栏导航 -----
    st.sidebar.markdown('<p class="main-title">📕 小红书达人评估</p>', unsafe_allow_html=True)
    # 导航菜单选项
    page = st.sidebar.radio(
        "导航",                            # 单选按钮标题
        ["📊 数据概览", "🏆 达人排行", "👤 达人详情", "📥 数据导出"],  # 页面选项
        label_visibility="collapsed"       # 隐藏标题
    )

    # 获取数据库实例
    db = get_db()

    # ----- 根据导航选择渲染对应页面 -----
    if page == "📊 数据概览":
        render_overview(db)      # 数据概览页
    elif page == "🏆 达人排行":
        render_ranking(db)       # 达人排行页
    elif page == "👤 达人详情":
        render_detail(db)        # 达人详情页
    elif page == "📥 数据导出":
        render_export(db)        # 数据导出页


def render_overview(db: Database):
    """
    渲染数据概览页面。
    展示关键指标统计和等级分布。
    参数:
        db: 数据库实例
    """
    # 页面标题
    st.markdown("## 📊 数据概览")
    st.markdown("---")

    # 获取统计数据
    user_count = db.get_user_count()       # 达人总数
    note_count = db.get_note_count()       # 笔记总数
    evaluations = db.get_all_evaluations()  # 评估结果

    # ----- 顶部指标卡片（4列布局） -----
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # 达人总数卡片
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{user_count}</div>
            <div class="metric-label">已采集达人</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # 笔记总数卡片
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <div class="metric-value">{note_count}</div>
            <div class="metric-label">已采集笔记</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        # 已评估达人数卡片
        eval_count = len(evaluations)
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <div class="metric-value">{eval_count}</div>
            <div class="metric-label">已评估达人</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        # S/A 级达人数卡片
        sa_count = sum(1 for e in evaluations if e.grade in ["S", "A"])
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
            <div class="metric-value">{sa_count}</div>
            <div class="metric-label">S/A 级达人</div>
        </div>
        """, unsafe_allow_html=True)

    # ----- 等级分布 -----
    if evaluations:
        st.markdown("### 合作推荐等级分布")
        # 统计各等级数量
        grade_counts = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
        for e in evaluations:
            grade_counts[e.grade] = grade_counts.get(e.grade, 0) + 1

        # 使用 Plotly 绘制柱状图
        fig = go.Figure(data=[
            go.Bar(
                x=list(grade_counts.keys()),     # X 轴：等级
                y=list(grade_counts.values()),   # Y 轴：数量
                marker_color=["#FF2442", "#FF6B35", "#FFA500", "#4CAF50", "#9E9E9E"],  # 各等级颜色
                text=list(grade_counts.values()),  # 柱子上显示数值
                textposition="auto"
            )
        ])
        # 图表样式设置
        fig.update_layout(
            xaxis_title="推荐等级",          # X 轴标题
            yaxis_title="达人数量",          # Y 轴标题
            height=400,                      # 图表高度
            template="plotly_white"          # 白色主题
        )
        st.plotly_chart(fig, use_container_width=True)  # 宽度自适应
    else:
        # 没有数据时的提示
        st.info("暂无评估数据。请先运行爬虫和评估流程。")


def render_ranking(db: Database):
    """
    渲染达人排行榜页面。
    以表格形式展示所有达人的评分和排名。
    参数:
        db: 数据库实例
    """
    # 页面标题
    st.markdown("## 🏆 达人排行榜")
    st.markdown("---")

    # 获取评估结果
    evaluations = db.get_all_evaluations()

    if not evaluations:
        st.info("暂无评估数据。")
        return

    # ----- 筛选控件 -----
    col1, col2, col3 = st.columns(3)

    with col1:
        # 等级筛选
        grade_filter = st.multiselect(
            "筛选推荐等级",                    # 标签
            ["S", "A", "B", "C", "D"],         # 选项
            default=["S", "A", "B", "C", "D"]  # 默认全选
        )

    with col2:
        # 排序字段
        sort_by = st.selectbox(
            "排序依据",
            ["综合评分", "互动率", "内容质量", "粉丝量级", "领域匹配"]
        )

    with col3:
        # 排序方向
        sort_order = st.selectbox("排序方向", ["降序", "升序"])

    # ----- 构建排行表格数据 -----
    rows = []
    # 同时获取用户数据用于显示头像
    all_users = {u.user_id: u for u in db.get_all_users()}

    for eval_item in evaluations:
        # 根据等级筛选
        if eval_item.grade not in grade_filter:
            continue
        # 获取对应用户信息
        user = all_users.get(eval_item.user_id)
        rows.append({
            "推荐等级": eval_item.grade,
            "昵称": eval_item.nickname,
            "综合评分": eval_item.total_score,
            "互动率(%)": eval_item.engagement_rate,
            "内容质量": eval_item.content_quality,
            "粉丝量级": eval_item.fans_score,
            "领域匹配": eval_item.domain_match,
            "更新频率": eval_item.update_frequency,
            "商业比例(%)": eval_item.commercial_ratio,
            "粉丝数": user.fans_count if user else 0,
            "用户ID": eval_item.user_id,
        })

    # 转为 DataFrame
    df = pd.DataFrame(rows)

    if df.empty:
        st.warning("没有符合筛选条件的达人")
        return

    # 排序字段映射
    sort_col_map = {
        "综合评分": "综合评分",
        "互动率": "互动率(%)",
        "内容质量": "内容质量",
        "粉丝量级": "粉丝量级",
        "领域匹配": "领域匹配",
    }
    # 执行排序
    sort_col = sort_col_map.get(sort_by, "综合评分")
    ascending = sort_order == "升序"
    df = df.sort_values(by=sort_col, ascending=ascending)

    # 添加排名列
    df.insert(0, "排名", range(1, len(df) + 1))

    # ----- 显示表格 -----
    st.dataframe(
        df,
        use_container_width=True,   # 宽度自适应
        hide_index=True,            # 隐藏索引列
        height=600,                 # 表格高度
        column_config={
            "推荐等级": st.column_config.TextColumn("等级", width="small"),
            "综合评分": st.column_config.ProgressColumn(
                "综合评分", min_value=0, max_value=100, format="%.1f"
            ),
        }
    )

    # 显示统计信息
    st.caption(f"共 {len(df)} 位达人 | 平均评分 {df['综合评分'].mean():.1f}")


def render_detail(db: Database):
    """
    渲染达人详情页面。
    展示单个达人的完整资料、评分雷达图和笔记列表。
    参数:
        db: 数据库实例
    """
    # 页面标题
    st.markdown("## 👤 达人详情")
    st.markdown("---")

    # 获取所有达人用于选择
    users = db.get_all_users()
    evaluations = db.get_all_evaluations()

    if not users:
        st.info("暂无达人数据。")
        return

    # 构建达人选择下拉框的选项
    user_options = {f"{u.nickname} ({u.user_id})": u.user_id for u in users}
    # 下拉框选择达人
    selected = st.selectbox("选择达人", list(user_options.keys()))
    # 获取选中的用户 ID
    selected_user_id = user_options[selected]

    # 获取选中达人的详细信息
    session = db.get_session()
    try:
        from models.database import UserModel, EvaluationModel  # 导入模型
        user = session.query(UserModel).filter_by(user_id=selected_user_id).first()
        evaluation = session.query(EvaluationModel).filter_by(user_id=selected_user_id).first()
    finally:
        session.close()

    if not user:
        st.error("未找到该达人信息")
        return

    # ----- 达人基本信息卡片 -----
    col_left, col_right = st.columns([1, 2])

    with col_left:
        # 显示头像
        if user.avatar_local and os.path.exists(user.avatar_local):
            # 如果有本地头像文件，直接显示
            st.image(user.avatar_local, width=200, caption=user.nickname)
        elif user.avatar:
            # 否则显示远程头像 URL
            st.image(user.avatar, width=200, caption=user.nickname)
        else:
            # 无头像时显示占位符
            st.markdown(f"### 👤 {user.nickname}")

        # 显示推荐等级
        if evaluation:
            # 根据等级选择样式
            grade_class = f"grade-{evaluation.grade.lower()}"
            st.markdown(
                f'<p class="{grade_class}">推荐等级: {evaluation.grade} '
                f'({evaluation.total_score:.1f}分)</p>',
                unsafe_allow_html=True
            )

    with col_right:
        # 显示基本信息
        st.markdown(f"**昵称**: {user.nickname}")
        st.markdown(f"**简介**: {user.desc or '未填写'}")
        st.markdown(f"**IP 属地**: {user.ip_location or '未知'}")
        st.markdown(f"**认证**: {'是' if user.verified else '否'}")
        st.markdown(f"**标签**: {user.tags or '无'}")

        # 关键数据指标（4列）
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("粉丝", f"{user.fans_count:,}")       # 粉丝数（千分位）
        m2.metric("关注", f"{user.following_count:,}")   # 关注数
        m3.metric("笔记", f"{user.notes_count:,}")       # 笔记数
        m4.metric("获赞收藏", f"{user.liked_count:,}")   # 获赞收藏

    # ----- 评分雷达图 -----
    if evaluation:
        st.markdown("### 📈 评估维度雷达图")

        # 雷达图维度和数值
        categories = ["互动率", "内容质量", "粉丝量级", "领域匹配", "更新频率", "商业表现"]
        # 商业表现 = 100 - 商业比例*2（比例越低越好）
        commercial_score = max(0, 100 - evaluation.commercial_ratio * 2)
        # 互动率评分转换
        engagement_score = min(100, evaluation.engagement_rate * 10)
        values = [
            engagement_score,                  # 互动率分
            evaluation.content_quality,        # 内容质量分
            evaluation.fans_score,             # 粉丝量级分
            evaluation.domain_match,           # 领域匹配度
            evaluation.update_frequency,       # 更新频率分
            commercial_score                   # 商业表现分
        ]

        # 创建雷达图
        fig = go.Figure(data=go.Scatterpolar(
            r=values + [values[0]],                      # 数据点（闭合）
            theta=categories + [categories[0]],          # 维度标签（闭合）
            fill="toself",                                # 填充区域
            fillcolor="rgba(255, 36, 66, 0.2)",          # 填充颜色（半透明红）
            line=dict(color="#FF2442", width=2),          # 边框线颜色
            marker=dict(size=8, color="#FF2442")          # 数据点标记
        ))

        # 图表样式
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,          # 显示径向轴
                    range=[0, 100],        # 范围 0-100
                    tickfont=dict(size=10)  # 刻度字号
                )
            ),
            height=450,                     # 图表高度
            template="plotly_white",        # 白色主题
            showlegend=False                # 不显示图例
        )

        st.plotly_chart(fig, use_container_width=True)

        # 评估数据明细（可折叠）
        with st.expander("查看评估数据明细"):
            detail_data = {
                "维度": categories,
                "得分": [f"{v:.1f}" for v in values],
                "说明": [
                    f"互动率 {evaluation.engagement_rate:.2f}%",
                    f"近期笔记互动中位数评分",
                    f"粉丝数 {user.fans_count:,}",
                    f"标签匹配度",
                    f"近30天更新评分",
                    f"广告占比 {evaluation.commercial_ratio:.1f}%",
                ]
            }
            st.table(pd.DataFrame(detail_data))

    # ----- 笔记列表 -----
    st.markdown("### 📝 近期笔记")
    notes = db.get_user_notes(selected_user_id)

    if notes:
        # 每行显示 4 篇笔记
        cols_per_row = 4
        for i in range(0, len(notes), cols_per_row):
            # 创建列布局
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(notes):
                    break  # 超出范围
                note = notes[idx]
                with col:
                    # 显示封面图
                    if note.cover_local and os.path.exists(note.cover_local):
                        st.image(note.cover_local, use_container_width=True)
                    elif note.cover_image:
                        st.image(note.cover_image, use_container_width=True)

                    # 显示笔记标题（截断过长标题）
                    title = note.title[:20] + "..." if len(note.title) > 20 else note.title
                    st.markdown(f"**{title or '无标题'}**")

                    # 显示互动数据
                    st.caption(
                        f"❤️ {note.liked_count} · ⭐ {note.collected_count} · "
                        f"💬 {note.comment_count}"
                    )
                    # 如果是广告笔记，标注
                    if note.is_ad:
                        st.markdown("🏷️ *合作笔记*")
    else:
        st.info("暂无笔记数据")


def render_export(db: Database):
    """
    渲染数据导出页面。
    提供 Excel 和 CSV 导出功能。
    参数:
        db: 数据库实例
    """
    # 页面标题
    st.markdown("## 📥 数据导出")
    st.markdown("---")

    # 获取统计数据
    user_count = db.get_user_count()
    note_count = db.get_note_count()
    eval_count = len(db.get_all_evaluations())

    # 显示当前数据量
    st.markdown(f"当前数据: **{user_count}** 位达人 · **{note_count}** 篇笔记 · **{eval_count}** 条评估")
    st.markdown("---")

    # ----- Excel 导出 -----
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Excel 报告")
        st.markdown("包含三个 Sheet: 评分排行、达人列表、笔记明细")
        # 导出按钮
        if st.button("📥 导出 Excel", type="primary", use_container_width=True):
            if eval_count == 0:
                st.warning("没有评估数据，请先运行评估")
            else:
                # 创建导出器并执行导出
                exporter = Exporter(db)
                filepath = exporter.export_excel()
                # 读取文件内容供下载
                with open(filepath, "rb") as f:
                    file_data = f.read()
                # 提供下载按钮
                st.download_button(
                    label="⬇️ 下载 Excel 文件",
                    data=file_data,
                    file_name=os.path.basename(filepath),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success(f"导出成功！文件: {filepath}")

    with col2:
        st.markdown("### 📄 CSV 导出")
        st.markdown("仅包含评分排行数据")
        # 导出按钮
        if st.button("📥 导出 CSV", use_container_width=True):
            if eval_count == 0:
                st.warning("没有评估数据，请先运行评估")
            else:
                exporter = Exporter(db)
                filepath = exporter.export_csv()
                if filepath:
                    with open(filepath, "rb") as f:
                        file_data = f.read()
                    st.download_button(
                        label="⬇️ 下载 CSV 文件",
                        data=file_data,
                        file_name=os.path.basename(filepath),
                        mime="text/csv"
                    )
                    st.success(f"导出成功！文件: {filepath}")


# 运行主函数
if __name__ == "__main__":
    main()
