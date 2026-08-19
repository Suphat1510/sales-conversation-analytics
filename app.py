from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px

from src.db import init_db, query_df
from src.importer import import_upload
from src.analytics import (
    rebuild_analytics, overview, tags_df, trend_df, lead_table,
    tag_deep_df, cooccurrence_df, response_impact_df, product_comparison_df,
    analysis_history_df, batch_overview, batch_tags_df, batch_tag_deep_df,
    batch_lead_table, save_analysis_snapshot,
)
from src.exporter import export_conversation_dataset

st.set_page_config(
    page_title="Sales Conversation Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()

ORANGE = "#F97316"
ORANGE_LIGHT = "#FDBA74"
BLACK = "#111111"
DARK = "#171717"
OFFWHITE = "#FFF7ED"
WHITE = "#FFFFFF"
GRAY = "#666666"
GRID = "#F3F4F6"


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
            .stApp {{
                background: linear-gradient(180deg, #fff7ed 0%, #ffffff 50%, #fff7ed 100%);
            }}
            [data-testid="stSidebar"] {{
                background: linear-gradient(180deg, #111111 0%, #1c1c1c 100%);
                border-right: 1px solid rgba(255,255,255,0.08);
            }}
            [data-testid="stSidebar"] * {{
                color: #ffffff;
            }}
            [data-testid="stSidebar"] .stRadio label,
            [data-testid="stSidebar"] .stSelectbox label,
            [data-testid="stSidebar"] .stCaption,
            [data-testid="stSidebar"] .stMarkdown p {{
                color: #ffffff !important;
            }}
            .block-container {{
                padding-top: 1.3rem;
                padding-bottom: 2rem;
                max-width: 1450px;
            }}
            .hero-box {{
                background: linear-gradient(135deg, #111111 0%, #27272a 45%, #f97316 160%);
                border-radius: 22px;
                padding: 24px 28px;
                color: white;
                margin-bottom: 1rem;
                box-shadow: 0 16px 40px rgba(17,17,17,0.16);
            }}
            .hero-title {{
                font-size: 2rem;
                font-weight: 800;
                margin-bottom: 0.25rem;
                line-height: 1.15;
            }}
            .hero-sub {{
                color: rgba(255,255,255,0.84);
                font-size: 0.98rem;
                margin-bottom: 0;
            }}
            .mini-chip-wrap {{
                display: flex;
                gap: 0.5rem;
                flex-wrap: wrap;
                margin-top: 0.85rem;
            }}
            .mini-chip {{
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 999px;
                padding: 0.35rem 0.7rem;
                font-size: 0.82rem;
            }}
            .section-title {{
                font-size: 1.1rem;
                font-weight: 700;
                color: #111111;
                margin-bottom: 0.2rem;
            }}
            .section-sub {{
                color: #666666;
                font-size: 0.92rem;
                margin-bottom: 0.7rem;
            }}
            .kpi-card {{
                background: white;
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 18px;
                padding: 16px 16px 14px 16px;
                box-shadow: 0 8px 22px rgba(17,17,17,0.06);
                min-height: 120px;
            }}
            .kpi-label {{
                color: #666666;
                font-size: 0.86rem;
                font-weight: 600;
                margin-bottom: 0.45rem;
            }}
            .kpi-value {{
                color: #111111;
                font-size: 1.8rem;
                font-weight: 800;
                line-height: 1.1;
                margin-bottom: 0.35rem;
            }}
            .kpi-note {{
                color: #f97316;
                font-size: 0.82rem;
                font-weight: 600;
            }}
            .panel-card {{
                background: white;
                border-radius: 20px;
                border: 1px solid rgba(0,0,0,0.06);
                padding: 1rem 1rem 0.6rem 1rem;
                box-shadow: 0 8px 22px rgba(17,17,17,0.05);
                margin-bottom: 1rem;
            }}
            .insight-card {{
                background: linear-gradient(180deg, #fff7ed 0%, #ffffff 100%);
                border-left: 5px solid #f97316;
                border-radius: 16px;
                padding: 14px 16px;
                margin-bottom: 0.8rem;
                border-top: 1px solid rgba(0,0,0,0.04);
                border-right: 1px solid rgba(0,0,0,0.04);
                border-bottom: 1px solid rgba(0,0,0,0.04);
            }}
            .insight-title {{
                color: #111111;
                font-size: 0.95rem;
                font-weight: 800;
                margin-bottom: 0.35rem;
            }}
            .insight-body {{
                color: #444444;
                font-size: 0.91rem;
                margin-bottom: 0;
            }}
            .stButton > button {{
                border-radius: 12px;
                border: 1px solid #f97316;
                background: #f97316;
                color: white;
                font-weight: 700;
                padding: 0.55rem 1rem;
            }}
            .stButton > button:hover {{
                background: #ea580c;
                border-color: #ea580c;
                color: white;
            }}
            .stDownloadButton > button {{
                border-radius: 12px;
                border: 1px solid #f97316;
            }}
            div[data-testid="stMetric"] {{
                background: white;
                border-radius: 16px;
                border: 1px solid rgba(0,0,0,0.06);
                padding: 12px 16px;
                box-shadow: 0 8px 22px rgba(17,17,17,0.05);
            }}
            div[data-testid="stDataFrame"] {{
                border-radius: 16px;
                overflow: hidden;
                border: 1px solid rgba(0,0,0,0.06);
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def fmt_num(value) -> str:
    try:
        return f"{int(value or 0):,}"
    except Exception:
        return "0"



def fmt_float(value, suffix: str = "") -> str:
    try:
        return f"{float(value or 0):.1f}{suffix}"
    except Exception:
        return f"0.0{suffix}"



def hero(title: str, subtitle: str, chips: list[str] | None = None) -> None:
    chips_html = "".join([f'<span class="mini-chip">{c}</span>' for c in (chips or [])])
    st.markdown(
        f"""
        <div class="hero-box">
            <div class="hero-title">{title}</div>
            <p class="hero-sub">{subtitle}</p>
            <div class="mini-chip-wrap">{chips_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def section(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="section-title">{title}</div>
        <div class="section-sub">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )



def kpi_card(label: str, value: str, note: str = "") -> str:
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-note">{note}</div>
    </div>
    """



def insight_card(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="insight-title">{title}</div>
            <p class="insight-body">{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )



def product_mix_df(product: str = "ALL") -> pd.DataFrame:
    where = "WHERE product_type=?" if product != "ALL" else ""
    params = (product,) if product != "ALL" else ()
    sql = f"""
        SELECT product_type, COUNT(*) AS conversations
        FROM conversations
        {where}
        GROUP BY product_type
        ORDER BY conversations DESC
    """
    return query_df(sql, params)



def top_opportunity(product: str = "ALL") -> pd.DataFrame:
    where = ["t.tag_type='interest'"]
    params = []
    if product != "ALL":
        where.append("c.product_type=?")
        params.append(product)
    sql = f"""
        SELECT t.tag_name,
               COUNT(DISTINCT t.conversation_key) AS conversations,
               AVG(COALESCE(m.purchase_signal_count,0)) AS avg_signal,
               AVG(COALESCE(m.first_response_minutes,0)) AS avg_response
        FROM conversation_tags t
        JOIN conversations c USING(conversation_key)
        LEFT JOIN conversation_metrics m USING(conversation_key)
        WHERE {' AND '.join(where)}
        GROUP BY t.tag_name
        ORDER BY conversations DESC, avg_signal DESC
        LIMIT 5
    """
    return query_df(sql, tuple(params))



def render_bar(df: pd.DataFrame, x: str, y: str, title: str = "", horizontal: bool = True):
    if horizontal:
        fig = px.bar(
            df,
            x=x,
            y=y,
            orientation="h",
            text=x,
            title=title,
            color_discrete_sequence=[ORANGE],
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
    else:
        fig = px.bar(df, x=x, y=y, text=y, title=title, color_discrete_sequence=[ORANGE])
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=42, b=20),
        font=dict(color=BLACK),
        title=dict(font=dict(size=18)),
        xaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False),
        yaxis=dict(showgrid=False),
    )
    return fig



def render_line(df: pd.DataFrame, x: str, y: str, title: str = ""):
    fig = px.line(df, x=x, y=y, markers=True, title=title)
    fig.update_traces(line=dict(color=ORANGE, width=4), marker=dict(size=10, color=BLACK))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=42, b=20),
        font=dict(color=BLACK),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False),
    )
    return fig



def render_pie(df: pd.DataFrame, names: str, values: str, title: str = ""):
    fig = px.pie(
        df,
        names=names,
        values=values,
        hole=0.58,
        title=title,
        color_discrete_sequence=[ORANGE, BLACK, ORANGE_LIGHT, "#FED7AA", "#FDBA74"],
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=42, b=20),
        font=dict(color=BLACK),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
    )
    fig.update_traces(textinfo="percent+label")
    return fig







def render_heatmap(pairs: pd.DataFrame, title: str = "Interest × Need"):
    pivot = pairs.pivot_table(index="item_a", columns="item_b", values="conversations", aggfunc="sum", fill_value=0)
    fig = px.imshow(
        pivot,
        text_auto=True,
        aspect="auto",
        color_continuous_scale=[[0, "#FFF7ED"], [0.45, "#FDBA74"], [1, "#F97316"]],
        title=title,
        labels=dict(x="ความต้องการ (Need)", y="ความสนใจ (Interest)", color="จำนวนห้อง"),
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=55, b=20),
        font=dict(color=BLACK),
        coloraxis_colorbar=dict(title="จำนวนห้อง"),
    )
    return fig


def render_quality_scatter(df: pd.DataFrame, title: str = "Demand vs Sales Quality"):
    plot_df = df.copy()
    plot_df["purchase_rate"] = pd.to_numeric(plot_df["purchase_rate"], errors="coerce").fillna(0)
    plot_df["dropoff_rate"] = pd.to_numeric(plot_df["dropoff_rate"], errors="coerce").fillna(0)
    plot_df["conversations"] = pd.to_numeric(plot_df["conversations"], errors="coerce").fillna(0)
    fig = px.scatter(
        plot_df,
        x="purchase_rate",
        y="dropoff_rate",
        size="conversations",
        hover_name="tag_name",
        hover_data={"conversations": True, "purchase_rate": ":.1f", "dropoff_rate": ":.1f"},
        title=title,
        labels={
            "purchase_rate": "ห้องที่มีสัญญาณซื้อ (%)",
            "dropoff_rate": "Drop-off (%)",
            "conversations": "จำนวนห้อง",
        },
        color_discrete_sequence=[ORANGE],
        size_max=42,
    )
    fig.update_traces(marker=dict(line=dict(width=1, color=BLACK), opacity=0.8))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=55, b=20),
        font=dict(color=BLACK),
        xaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False),
    )
    return fig


def render_response_lines(df: pd.DataFrame, title: str = "ผลของความเร็วในการตอบ"):
    plot_df = df.melt(
        id_vars=["response_bucket"],
        value_vars=["purchase_rate", "dropoff_rate"],
        var_name="metric",
        value_name="rate",
    )
    plot_df["metric"] = plot_df["metric"].map({
        "purchase_rate": "มีสัญญาณซื้อ",
        "dropoff_rate": "Drop-off",
    })
    fig = px.line(
        plot_df,
        x="response_bucket",
        y="rate",
        color="metric",
        markers=True,
        title=title,
        labels={"response_bucket": "ช่วงเวลาตอบ", "rate": "สัดส่วน (%)", "metric": "ตัวชี้วัด"},
        color_discrete_map={"มีสัญญาณซื้อ": ORANGE, "Drop-off": BLACK},
    )
    fig.update_traces(line=dict(width=4), marker=dict(size=9))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=55, b=20),
        font=dict(color=BLACK),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False, ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def render_purchase_funnel(df: pd.DataFrame, title: str = "Purchase Signals"):
    plot_df = df.sort_values("conversations", ascending=False).copy()
    fig = px.funnel(
        plot_df,
        x="conversations",
        y="tag_name",
        title=title,
        labels={"conversations": "จำนวนห้อง", "tag_name": "สัญญาณซื้อ"},
        color_discrete_sequence=[ORANGE],
    )
    fig.update_traces(textposition="inside", textinfo="value+percent initial")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=55, b=20),
        font=dict(color=BLACK),
    )
    return fig


def render_lead_scatter(df: pd.DataFrame, title: str = "Lead Opportunity Map"):
    plot_df = df.copy()
    for col in ["message_count", "purchase_signal_count", "first_response_minutes"]:
        plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce").fillna(0)
    fig = px.scatter(
        plot_df,
        x="purchase_signal_count",
        y="message_count",
        size="message_count",
        color="product_type",
        hover_name="conversation_id",
        hover_data=["interests", "needs", "pain_points", "signals", "first_response_minutes"],
        title=title,
        labels={
            "purchase_signal_count": "จำนวนสัญญาณซื้อ",
            "message_count": "จำนวนข้อความ",
            "product_type": "Product",
        },
        color_discrete_map={"SPA": ORANGE, "FNB": BLACK},
        size_max=34,
    )
    fig.update_traces(marker=dict(opacity=0.78, line=dict(width=1, color=WHITE)))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=55, b=20),
        font=dict(color=BLACK),
        xaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False, dtick=1),
        yaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False),
    )
    return fig

def sales_action_for(tag_name: str, tag_type: str, product: str) -> str:
    name = str(tag_name)
    if tag_type == "purchase_signal":
        return "ให้ Sales ติดตามก่อนกลุ่มอื่น พร้อมเตรียมราคา แพ็กเกจ หรือขั้นตอนถัดไปให้ตอบได้ทันที"
    if tag_type == "pain_point":
        return f"ใช้ประเด็น ‘{name}’ เป็น pain point ตอนเปิดบทสนทนา แล้วเชื่อมไปยังฟีเจอร์ที่ช่วยแก้ปัญหานี้"
    if tag_type == "need":
        return f"จัดชุดการขายโดยเริ่มจากความต้องการ ‘{name}’ และเสนอฟีเจอร์ที่ตอบโจทย์นี้ก่อนรายละเอียดอื่น"
    if product == "SPA":
        return f"ใช้ ‘{name}’ เป็นหัวข้อหลักในการคุยกับธุรกิจบริการ/สปา และจับคู่กับ Booking, Membership หรือ Package หากเกี่ยวข้อง"
    if product == "FNB":
        return f"ใช้ ‘{name}’ เป็นหัวข้อหลักกับร้านอาหาร และเชื่อมต่อกับ Stock, Kitchen, QR Order หรือ Multi Branch ตามบริบท"
    return f"ใช้ ‘{name}’ เป็นประเด็นนำในการขาย และดูหัวข้อที่มักเกิดร่วมกันก่อน Follow-up"


def thai_dashboard_summary(product: str) -> list[tuple[str, str]]:
    stats = overview(product)
    needs = tag_deep_df("need", product, 5)
    interests = tag_deep_df("interest", product, 5)
    pains = tag_deep_df("pain_point", product, 5)
    rows = []
    if not interests.empty:
        r = interests.iloc[0]
        rows.append(("ลูกค้าสนใจอะไรที่สุด", f"ตอนนี้หัวข้อที่พบมากที่สุดคือ <b>{r['tag_name']}</b> พบใน {int(r['conversations'])} ห้อง และในกลุ่มนี้ {float(r['purchase_rate'] or 0):.1f}% มีสัญญาณซื้อ"))
    if not needs.empty:
        r = needs.iloc[0]
        rows.append(("ลูกค้าต้องการอะไร", f"ความต้องการที่เด่นที่สุดคือ <b>{r['tag_name']}</b> พบใน {int(r['conversations'])} ห้อง จึงควรเป็นหนึ่งในหัวข้อหลักที่ Sales ใช้ถามและนำเสนอ"))
    if not pains.empty:
        r = pains.iloc[0]
        rows.append(("ปัญหาที่ควรหยิบไปใช้ตอนขาย", f"Pain point ที่พบมากคือ <b>{r['tag_name']}</b> พบใน {int(r['conversations'])} ห้อง โดยกลุ่มนี้มี Drop-off {float(r['dropoff_rate'] or 0):.1f}% ควรตอบให้ตรงประเด็นและเร็ว"))
    rows.append(("ภาพรวมโอกาสการขาย", f"จากทั้งหมด {int(stats.get('conversations') or 0):,} ห้อง มี {float(stats.get('purchase_signal_rate') or 0):.1f}% ที่พบสัญญาณซื้อ และ Drop-off อยู่ที่ {float(stats.get('dropoff_rate') or 0):.1f}%"))
    return rows


def empty_state(msg: str = "ยังไม่มีข้อมูล"):
    st.info(msg)


inject_css()

with st.sidebar:
    st.markdown("## 🟧 Sales Analytics")
    st.caption("Conversation Insight สำหรับ POS SPA และ POS F&B")
    page = st.radio(
        "เมนู",
        ["Dashboard", "Customer Insight", "Sales Opportunity", "Analysis History", "Import Data", "Data Management"],
        format_func=lambda x: {
            "Dashboard": "📈 Dashboard",
            "Customer Insight": "🧠 Customer Insight",
            "Sales Opportunity": "🔥 Sales Opportunity",
            "Analysis History": "🕘 Analysis History",
            "Import Data": "📥 Import Data",
            "Data Management": "🗂️ Data Management",
        }[x],
        label_visibility="collapsed",
    )
    product = st.selectbox(
        "Product",
        ["ALL", "SPA", "FNB"],
        format_func=lambda x: {"ALL": "ทั้งหมด", "SPA": "POS SPA", "FNB": "POS F&B"}[x],
    )
    st.markdown("---")
    st.caption("หลักการทำงาน")
    st.caption("• Upload เพิ่มได้เรื่อย ๆ")
    st.caption("• ตรวจข้อมูลซ้ำอัตโนมัติ")
    st.caption("• แยก Logic ระหว่าง SPA / F&B")
    st.caption("• ใช้ SQLite + Python + Dashboard")

product_label = {"ALL": "ทุกผลิตภัณฑ์", "SPA": "POS SPA", "FNB": "POS F&B"}[product]

if page == "Dashboard":
    stats = overview(product)
    hero(
        "Sales Conversation Analytics",
        f"ภาพรวมข้อมูลบทสนทนาและสัญญาณทางธุรกิจของ {product_label} เพื่อให้ทีม Sales ดูง่าย ใช้งานเร็ว และตัดสินใจต่อได้ทันที",
        [product_label, "Incremental Import", "Black • Orange • White Theme"],
    )

    cols = st.columns(6)
    cards = [
        ("ห้องสนทนา", fmt_num(stats.get("conversations")), "Conversation ทั้งหมด"),
        ("ข้อความ", fmt_num(stats.get("messages")), "Message ที่อยู่ในระบบ"),
        ("ตอบครั้งแรก", fmt_float(stats.get("avg_first_response"), " นาที"), "ยิ่งต่ำยิ่งดี"),
        ("เวลาคุยเฉลี่ยต่อรอบ", fmt_float(stats.get("avg_duration"), " นาที"), "ตัดช่วงเงียบเกิน 24 ชม."),
        ("Drop-off", fmt_float(stats.get("dropoff_rate"), "%"), "ลูกค้าหายหลังทีมตอบ"),
        ("Purchase Signal", fmt_float(stats.get("purchase_signal_rate"), "%"), "ห้องที่มีสัญญาณซื้อ"),
    ]
    for col, (label, value, note) in zip(cols, cards):
        col.markdown(kpi_card(label, value, note), unsafe_allow_html=True)

    section("Executive Overview", "ดูภาพรวมแนวโน้ม ปริมาณข้อมูล และสัดส่วนผลิตภัณฑ์ที่เข้ามาในระบบ")
    left, right = st.columns([1.6, 1])
    trend = trend_df(product)
    mix = product_mix_df(product)
    with left:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        if not trend.empty:
            st.plotly_chart(render_line(trend, "month", "conversations", "Conversation Trend"), config={"displaylogo": False, "responsive": True})
        else:
            empty_state("ยังไม่มีข้อมูล trend")
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        if not mix.empty:
            st.plotly_chart(render_pie(mix, "product_type", "conversations", "Product Mix"), config={"displaylogo": False, "responsive": True})
        else:
            empty_state("ยังไม่มีข้อมูล product mix")
        st.markdown("</div>", unsafe_allow_html=True)

    section("Need & Interest Snapshot", "ใช้ดูว่าตลาดต้องการอะไรและกำลังสนใจอะไรบ่อยที่สุดในตอนนี้")
    left, right = st.columns(2)
    needs = tags_df("need", product, 10)
    interests = tags_df("interest", product, 10)
    with left:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        if not needs.empty:
            st.plotly_chart(render_bar(needs.sort_values("conversations", ascending=True), "conversations", "tag_name", "Top Customer Needs"), config={"displaylogo": False, "responsive": True})
        else:
            empty_state()
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        if not interests.empty:
            st.plotly_chart(render_bar(interests.sort_values("conversations", ascending=True), "conversations", "tag_name", "Top Customer Interests"), config={"displaylogo": False, "responsive": True})
        else:
            empty_state()
        st.markdown("</div>", unsafe_allow_html=True)

    section("สรุปสำหรับทีม Sales", "อ่านส่วนนี้ก่อนกราฟ: ระบบสรุปให้เป็นภาษาไทยว่าตอนนี้ควรสนใจอะไรและนำไปใช้อย่างไร")
    summary_rows = thai_dashboard_summary(product)
    c1, c2 = st.columns(2)
    for idx, (title, body) in enumerate(summary_rows):
        with (c1 if idx % 2 == 0 else c2):
            insight_card(title, body)

elif page == "Customer Insight":
    hero(
        "Customer Insight แบบเจาะลึก",
        f"ดูมากกว่าอันดับ Top: วิเคราะห์ว่าแต่ละความต้องการ/ความสนใจสัมพันธ์กับสัญญาณซื้อ การหายจากแชท ความเร็วในการตอบ และหัวข้ออื่นอย่างไร สำหรับ {product_label}",
        [product_label, "Demand", "Purchase Rate", "Drop-off", "Co-occurrence", "Response Impact"],
    )

    tabs = st.tabs(["ภาพรวมเชิงลึก", "Needs", "Interests", "Pain Points", "Purchase Signals", "พฤติกรรมการตอบ"])

    with tabs[0]:
        section("Deep Insight Summary", "สรุปประเด็นที่น่าสนใจที่สุดจากหลายมิติ ไม่ได้ดูแค่จำนวนครั้งที่ถูกพูดถึง")
        interests = tag_deep_df("interest", product, 10)
        needs = tag_deep_df("need", product, 10)
        pains = tag_deep_df("pain_point", product, 10)
        pairs = cooccurrence_df("interest", "need", product, 15)

        a, b = st.columns(2)
        with a:
            if not interests.empty:
                top = interests.iloc[0]
                insight_card("ความสนใจที่เด่นที่สุด", f"<b>{top['tag_name']}</b> พบ {int(top['conversations'])} ห้อง • มีสัญญาณซื้อ {float(top['purchase_rate'] or 0):.1f}% • Drop-off {float(top['dropoff_rate'] or 0):.1f}%<br><br><b>Sales Action:</b> {sales_action_for(top['tag_name'], 'interest', product)}")
            if not pains.empty:
                top = pains.iloc[0]
                insight_card("Pain Point หลัก", f"<b>{top['tag_name']}</b> พบ {int(top['conversations'])} ห้อง • ตอบครั้งแรกเฉลี่ย {float(top['avg_first_response_minutes'] or 0):.1f} นาที • Drop-off {float(top['dropoff_rate'] or 0):.1f}%<br><br><b>Sales Action:</b> {sales_action_for(top['tag_name'], 'pain_point', product)}")
        with b:
            if not needs.empty:
                top = needs.iloc[0]
                insight_card("ความต้องการหลักของลูกค้า", f"<b>{top['tag_name']}</b> พบ {int(top['conversations'])} ห้อง • ถูกพูดถึง {int(top['mentions'])} ครั้ง • สัญญาณซื้อ {float(top['purchase_rate'] or 0):.1f}%<br><br><b>Sales Action:</b> {sales_action_for(top['tag_name'], 'need', product)}")
            if not pairs.empty:
                top = pairs.iloc[0]
                insight_card("สิ่งที่ลูกค้ามักพูดถึงร่วมกัน", f"ลูกค้ามักสนใจ <b>{top['item_a']}</b> พร้อมกับต้องการ <b>{top['item_b']}</b> พบคู่กัน {int(top['conversations'])} ห้อง และกลุ่มนี้มีสัญญาณซื้อ {float(top['purchase_rate'] or 0):.1f}%")

        if not pairs.empty:
            section("Interest × Need ที่เกิดร่วมกัน", "Heatmap ช่วยให้เห็นทันทีว่าความสนใจใดมักเกิดพร้อมกับความต้องการใด เหมาะกับการหา bundle สำหรับ Sales")
            st.plotly_chart(render_heatmap(pairs, "Heatmap: Interest × Need"), config={"displaylogo": False, "responsive": True})
            with st.expander("ดูข้อมูลคู่หัวข้อแบบตาราง"):
                st.dataframe(pairs, width="stretch", hide_index=True)

        if product == "ALL":
            comp = product_comparison_df()
            if not comp.empty:
                section("SPA vs F&B", "เปรียบเทียบคุณภาพบทสนทนาและสัญญาณขายระหว่างสองผลิตภัณฑ์")
                st.dataframe(comp, width="stretch", hide_index=True)

    tab_map = [
        (tabs[1], "need", "ความต้องการของลูกค้า", "ดูว่า Need ไหนมี demand สูง และ Need ไหนมีแนวโน้มซื้อสูงกว่ากัน"),
        (tabs[2], "interest", "ความสนใจของลูกค้า", "แยกให้ออกว่าอะไรถูกถามบ่อย และอะไรมีคุณค่าต่อ Sales จริง"),
        (tabs[3], "pain_point", "Pain Point ของลูกค้า", "ดูว่าปัญหาไหนเกิดบ่อยและสัมพันธ์กับการหายจากบทสนทนามากที่สุด"),
        (tabs[4], "purchase_signal", "สัญญาณซื้อ", "ดูสัญญาณที่ช่วยบอกว่าห้องไหนควร Follow-up ก่อน"),
    ]
    for tab, tag_type, title, subtitle in tab_map:
        with tab:
            section(title, subtitle)
            df = tag_deep_df(tag_type, product, 30)
            if df.empty:
                empty_state()
                continue
            top = df.iloc[0]
            insight_card(
                "อ่านตัวเลขนี้อย่างไร",
                f"อันดับหนึ่งคือ <b>{top['tag_name']}</b> พบใน {int(top['conversations'])} ห้อง แต่ที่สำคัญคือกลุ่มนี้มีสัญญาณซื้อ {float(top['purchase_rate'] or 0):.1f}% และ Drop-off {float(top['dropoff_rate'] or 0):.1f}% ดังนั้นอย่าดูแค่จำนวนห้องอย่างเดียว<br><br><b>สิ่งที่ Sales ควรทำ:</b> {sales_action_for(top['tag_name'], tag_type, product)}",
            )
            if tag_type == "purchase_signal":
                st.plotly_chart(render_purchase_funnel(df.head(12), "เส้นทางสัญญาณการซื้อที่พบในบทสนทนา"), config={"displaylogo": False, "responsive": True})
                st.caption("Funnel ใช้เพื่อดูว่าสัญญาณเชิงการขายใดพบมากไปน้อย ไม่ได้หมายความว่าลูกค้าทุกคนต้องผ่านแต่ละขั้นตามลำดับ")
            else:
                left, right = st.columns([1.05, 1])
                with left:
                    st.plotly_chart(render_bar(df.head(12).sort_values("conversations", ascending=True), "conversations", "tag_name", f"{title}: อันดับตามจำนวนห้อง"), config={"displaylogo": False, "responsive": True})
                with right:
                    st.plotly_chart(render_quality_scatter(df.head(20), "Demand เทียบกับคุณภาพโอกาสขาย"), config={"displaylogo": False, "responsive": True})
                    st.caption("จุดที่อยู่ทางขวา = มี Purchase Signal สูง • จุดที่อยู่ด้านล่าง = Drop-off ต่ำ • จุดใหญ่ = พบในหลายห้อง")
            st.dataframe(
                df.rename(columns={
                    "tag_name":"หัวข้อ", "conversations":"จำนวนห้อง", "mentions":"จำนวนครั้งที่พูดถึง",
                    "purchase_rate":"มีสัญญาณซื้อ (%)", "avg_purchase_signals":"สัญญาณซื้อเฉลี่ย",
                    "dropoff_rate":"Drop-off (%)", "avg_first_response_minutes":"ตอบครั้งแรกเฉลี่ย (นาที)",
                    "avg_duration_minutes":"เวลาคุยเฉลี่ยต่อรอบ (นาที)"
                }),
                width="stretch", hide_index=True,
            )

    with tabs[5]:
        section("Response Time Impact", "ดูว่าความเร็วในการตอบสัมพันธ์กับ Purchase Signal และ Drop-off อย่างไร")
        rdf = response_impact_df(product)
        if rdf.empty:
            empty_state("ยังไม่มี timestamp เพียงพอสำหรับวิเคราะห์ Response Time")
        else:
            st.plotly_chart(render_response_lines(rdf, "Purchase Signal และ Drop-off เมื่อเวลาตอบเปลี่ยนไป"), config={"displaylogo": False, "responsive": True})
            with st.expander("ดูตัวเลข Response Time แบบตาราง"):
                st.dataframe(rdf.rename(columns={"response_bucket":"ช่วงเวลาตอบ", "conversations":"จำนวนห้อง", "purchase_rate":"มีสัญญาณซื้อ (%)", "dropoff_rate":"Drop-off (%)", "avg_response":"เวลาตอบเฉลี่ย"}), width="stretch", hide_index=True)
            best = rdf.sort_values("purchase_rate", ascending=False).iloc[0]
            worst = rdf.sort_values("dropoff_rate", ascending=False).iloc[0]
            insight_card("สิ่งที่ทีม Sales ใช้ได้ทันที", f"ช่วงเวลาตอบที่มี Purchase Signal สูงสุดคือ <b>{best['response_bucket']}</b> ({float(best['purchase_rate']):.1f}%) ส่วนช่วงที่ Drop-off สูงสุดคือ <b>{worst['response_bucket']}</b> ({float(worst['dropoff_rate']):.1f}%) ใช้เป็นข้อมูลประกอบการตั้ง SLA การตอบแชทได้")

elif page == "Sales Opportunity":
    hero(
        "Sales Opportunity",
        f"จัดลำดับ Lead ที่ควร Follow-up ก่อนสำหรับ {product_label}",
        [product_label, "Lead Priority", "Follow-up Ready"],
    )

    # =========================
    # Filter
    # =========================

    min_sig = st.slider(
        "Purchase signal ขั้นต่ำ",
        1,
        10,
        1
    )

    df = lead_table(product, min_sig)

    if df.empty:
        empty_state("ยังไม่มี Lead ตามเงื่อนไขที่เลือก")

    else:
        df = df.copy()

        # =========================
        # เตรียมข้อมูล
        # =========================

        df["message_count"] = pd.to_numeric(
            df["message_count"],
            errors="coerce"
        ).fillna(0)

        df["purchase_signal_count"] = pd.to_numeric(
            df["purchase_signal_count"],
            errors="coerce"
        ).fillna(0)

        df["first_response_minutes"] = pd.to_numeric(
            df["first_response_minutes"],
            errors="coerce"
        ).fillna(0)

        # =========================
        # Priority Score
        # =========================

        signal_score = (
            df["purchase_signal_count"]
            .clip(upper=5)
            / 5
            * 60
        )

        engagement_score = (
            df["message_count"]
            .clip(upper=30)
            / 30
            * 25
        )

        response_score = (
            (30 - df["first_response_minutes"].clip(upper=30))
            / 30
            * 15
        )

        df["priority_score"] = (
            signal_score
            + engagement_score
            + response_score
        ).round(0)

        df["priority_level"] = pd.cut(
            df["priority_score"],
            bins=[-1, 39, 69, 100],
            labels=["Cold", "Warm", "Hot"]
        )

        df = df.sort_values(
            ["priority_score", "purchase_signal_count"],
            ascending=[False, False]
        )

        # =========================
        # สรุปจำนวน Lead
        # =========================

        hot_count = int(
            (df["priority_level"] == "Hot").sum()
        )

        warm_count = int(
            (df["priority_level"] == "Warm").sum()
        )

        cold_count = int(
            (df["priority_level"] == "Cold").sum()
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Lead ทั้งหมด",
            f"{len(df):,}"
        )

        c2.metric(
            "🔥 Hot Lead",
            f"{hot_count:,}"
        )

        c3.metric(
            "🟠 Warm Lead",
            f"{warm_count:,}"
        )

        c4.metric(
            "⚪ Cold Lead",
            f"{cold_count:,}"
        )

        # =========================
        # คำอธิบาย
        # =========================

        st.info(
            """
            **วิธีอ่านตาราง**

            🔥 Hot = ควร Follow-up ก่อน  
            🟠 Warm = มีความสนใจ ควรติดตามต่อ  
            ⚪ Cold = ยังไม่มีสัญญาณมากพอ

            คะแนน Priority คำนวณจาก Purchase Signal,
            จำนวนข้อความในการสนทนา และความเร็วในการตอบ
            """
        )

        # =========================
        # ตาราง
        # =========================

        section(
            "Lead ที่ควรติดตาม",
            "เรียงจาก Lead ที่มี Priority สูงที่สุดลงมา"
        )

        display_cols = [
            "priority_level",
            "priority_score",
            "conversation_id",
            "product_type",
            "started_at",
            "purchase_signal_count",
            "signals",
            "interests",
            "needs",
            "message_count",
            "first_response_minutes",
        ]

        display_df = df[
            [
                col
                for col in display_cols
                if col in df.columns
            ]
        ].copy()

        display_df = display_df.rename(
            columns={
                "priority_level": "ระดับ",
                "priority_score": "คะแนน Priority",
                "conversation_id": "ห้องสนทนา",
                "product_type": "ระบบ",
                "started_at": "วันที่เริ่มคุย",
                "purchase_signal_count": "จำนวนสัญญาณซื้อ",
                "signals": "สัญญาณซื้อที่พบ",
                "interests": "สิ่งที่ลูกค้าสนใจ",
                "needs": "สิ่งที่ลูกค้าต้องการ",
                "message_count": "จำนวนข้อความ",
                "first_response_minutes": "ตอบครั้งแรก (นาที)",
            }
        )

        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            column_config={
                "คะแนน Priority": st.column_config.ProgressColumn(
                    "คะแนน Priority",
                    help="คะแนน 0–100 ยิ่งสูงยิ่งควร Follow-up ก่อน",
                    min_value=0,
                    max_value=100,
                ),
                "จำนวนสัญญาณซื้อ": st.column_config.NumberColumn(
                    "จำนวนสัญญาณซื้อ",
                    format="%d"
                ),
                "ตอบครั้งแรก (นาที)": st.column_config.NumberColumn(
                    "ตอบครั้งแรก (นาที)",
                    format="%.1f"
                ),
            }
        )

elif page == "Analysis History":
    hero(
        "Analysis History",
        "ย้อนดูผลวิเคราะห์แต่ละรอบที่เคยทำไว้ได้ทันที โดยไม่ต้องประมวลผลข้อมูลเดิมซ้ำ",
        [product_label, "Saved Results", "No Re-analysis", "Batch History"],
    )
    hist = analysis_history_df(product)
    if hist.empty:
        empty_state("ยังไม่มีประวัติการนำเข้าข้อมูล")
    else:
        show = hist.copy()
        show["ชื่อรอบ"] = show.apply(
            lambda r: f"{r['product_type']} • {r['period_label'] or 'ไม่ระบุรอบ'} • {r['source_filename']}", axis=1
        )
        section("เลือกรอบที่ต้องการย้อนดู", "ผลที่เปิดจากหน้านี้เป็น Snapshot ของรอบนั้น ไม่ถูกผลวิเคราะห์รอบใหม่ทับ")
        selected_label = st.selectbox("Analysis Batch", show["ชื่อรอบ"].tolist())
        row = show.loc[show["ชื่อรอบ"].eq(selected_label)].iloc[0]
        batch_id = row["batch_id"]

        if row["analysis_status"] != "วิเคราะห์แล้ว":
            st.warning("รอบนี้ถูกนำเข้าก่อนมีระบบ Analysis History จึงยังไม่มี Snapshot แยกไว้")
            if st.button("บันทึกผลปัจจุบันเป็น History", type="primary"):
                n = save_analysis_snapshot(batch_id)
                st.success(f"บันทึกผลเดิมเข้า History แล้ว {n:,} ห้อง โดยไม่วิเคราะห์ใหม่")
                st.rerun()
        else:
            stats = batch_overview(batch_id)
            cols = st.columns(6)
            cards = [
                ("ห้องในรอบนี้", fmt_num(stats.get("conversations")), "Snapshot ของ batch นี้"),
                ("ข้อความ", fmt_num(stats.get("messages")), "จำนวนข้อความในผลรอบนี้"),
                ("ตอบครั้งแรก", fmt_float(stats.get("avg_first_response"), " นาที"), "เวลาเฉลี่ยก่อนตอบลูกค้า"),
                ("เวลาคุยเฉลี่ยต่อรอบ", fmt_float(stats.get("avg_duration"), " นาที"), "เงียบเกิน 24 ชม. = รอบใหม่"),
                ("Drop-off", fmt_float(stats.get("dropoff_rate"), "%"), "สัดส่วนห้องที่ลูกค้าหาย"),
                ("Purchase Signal", fmt_float(stats.get("purchase_signal_rate"), "%"), "ห้องที่มีสัญญาณซื้อ"),
            ]
            for col, (label, value, note) in zip(cols, cards):
                col.markdown(kpi_card(label, value, note), unsafe_allow_html=True)

            st.caption(f"วิเคราะห์เมื่อ: {row['analyzed_at']} • Batch: {batch_id}")
            tabs = st.tabs(["สรุป Insight", "Deep Insight", "Sales Leads", "ข้อมูล Batch"] )
            with tabs[0]:
                a, b = st.columns(2)
                needs = batch_tags_df(batch_id, "need", 10)
                interests = batch_tags_df(batch_id, "interest", 10)
                with a:
                    section("ลูกค้าต้องการอะไร", "Need ที่เด่นในรอบที่เลือก")
                    if not needs.empty:
                        st.plotly_chart(render_bar(needs.sort_values("conversations", ascending=True), "conversations", "tag_name", "Customer Needs"), config={"displaylogo": False, "responsive": True})
                    else:
                        empty_state()
                with b:
                    section("ลูกค้าสนใจอะไร", "Interest ที่เด่นในรอบที่เลือก")
                    if not interests.empty:
                        st.plotly_chart(render_bar(interests.sort_values("conversations", ascending=True), "conversations", "tag_name", "Customer Interests"), config={"displaylogo": False, "responsive": True})
                    else:
                        empty_state()
            with tabs[1]:
                dtype = st.selectbox("เลือกมิติ", ["need", "interest", "pain_point", "purchase_signal"], format_func=lambda x: {"need":"Needs", "interest":"Interests", "pain_point":"Pain Points", "purchase_signal":"Purchase Signals"}[x], key="history_deep_type")
                deep = batch_tag_deep_df(batch_id, dtype, 30)
                if deep.empty:
                    empty_state()
                else:
                    st.dataframe(deep.rename(columns={
                        "tag_name":"หัวข้อ", "conversations":"จำนวนห้อง", "mentions":"จำนวนครั้งที่พูดถึง",
                        "purchase_rate":"มีสัญญาณซื้อ (%)", "avg_purchase_signals":"สัญญาณซื้อเฉลี่ย",
                        "dropoff_rate":"Drop-off (%)", "avg_first_response_minutes":"ตอบครั้งแรกเฉลี่ย (นาที)",
                        "avg_duration_minutes":"เวลาคุยเฉลี่ยต่อรอบ (นาที)"
                    }), width="stretch", hide_index=True)
            with tabs[2]:
                min_sig_hist = st.slider("Purchase signal ขั้นต่ำ", 1, 10, 1, key="history_min_sig")
                leads = batch_lead_table(batch_id, min_sig_hist)
                if leads.empty:
                    empty_state("ไม่มี Lead ตามเงื่อนไข")
                else:
                    st.dataframe(leads, width="stretch", hide_index=True)
            with tabs[3]:
                st.dataframe(pd.DataFrame([{
                    "Batch": batch_id,
                    "Product": row["product_type"],
                    "Period": row["period_label"],
                    "File": row["source_filename"],
                    "Imported at": row["imported_at"],
                    "Analyzed at": row["analyzed_at"],
                    "Conversations": row["conversations_analyzed"],
                    "Rows inserted": row["rows_inserted"],
                    "Rows skipped": row["rows_skipped"],
                }]), width="stretch", hide_index=True)

elif page == "Import Data":
    hero(
        "Import Conversation Data",
        "อัปโหลดไฟล์ ZIP / CSV / JSON เพื่อเพิ่มข้อมูลเข้า Dashboard โดยระบบจะตรวจซ้ำ แปลงโครงสร้าง และคำนวณผลวิเคราะห์ให้อัตโนมัติ",
        ["ZIP", "CSV", "JSON", "Incremental Import"],
    )
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        section("อัปโหลดข้อมูล", "รองรับไฟล์ ZIP ที่ภายในมี CSV/JSON หรืออัปโหลด CSV/JSON โดยตรง")
        ptype = st.selectbox("ประเภทข้อมูล", ["SPA", "FNB"], format_func=lambda x: "POS SPA" if x == "SPA" else "POS F&B")
        period = st.text_input("รอบข้อมูล (ไม่บังคับ)", placeholder="เช่น 2026-08")
        uploaded = st.file_uploader("เลือกไฟล์", type=["zip", "csv", "json"])
        if st.button("Upload & Analyze", type="primary", disabled=uploaded is None):
            try:
                progress = st.progress(0, text="กำลังเตรียมข้อมูล...")
                status_box = st.empty()
                detail_box = st.empty()

                def on_progress(stage, current, total, detail):
                    total = max(int(total or 1), 1)
                    current = min(int(current or 0), total)
                    if stage in {"prepare", "import", "import_done"}:
                        pct = int((current / total) * 45)
                        label = "กำลังอ่านและบันทึกไฟล์"
                    else:
                        pct = 45 + int((current / total) * 50)
                        label = "กำลังวิเคราะห์บทสนทนา"
                    pct = max(0, min(pct, 95))
                    progress.progress(pct, text=f"{label} • {pct}%")
                    status_box.markdown(f"**{detail}**")
                    if stage == "analytics":
                        detail_box.caption(f"วิเคราะห์แล้ว {current:,} จาก {total:,} ห้อง • เหลือ {max(total-current,0):,} ห้อง")

                result = import_upload(uploaded.name, uploaded.getvalue(), ptype, period, progress_callback=on_progress)
                if result.is_duplicate:
                    progress.progress(100, text="พบข้อมูลเดิม • 100%")
                    status_box.markdown("**ไฟล์นี้เคยถูกนำเข้าและวิเคราะห์แล้ว จึงไม่วิเคราะห์ซ้ำ**")
                    detail_box.caption(f"Batch เดิม: {result.existing_batch_id or result.batch_id} • เปิดดูผลเดิมได้ที่เมนู Analysis History")
                    rebuilt = 0
                    st.info("ไม่เสียเวลาวิเคราะห์ซ้ำ ระบบใช้ผลที่บันทึกไว้เดิม")
                else:
                    rebuilt = rebuild_analytics(ptype, batch_id=result.batch_id, progress_callback=on_progress)
                    progress.progress(100, text="เสร็จสมบูรณ์ • 100%")
                    status_box.markdown("**สร้างข้อมูลสำหรับ Dashboard และบันทึก History เรียบร้อยแล้ว**")
                    detail_box.caption(f"เพิ่ม {result.rows_inserted:,} ข้อความ • ข้าม {result.rows_skipped:,} • วิเคราะห์ {rebuilt:,} ห้องใหม่/ห้องที่มีการเปลี่ยนแปลง")
                    st.success(
                        f"สำเร็จ: เพิ่ม {result.rows_inserted:,} ข้อความ | ข้าม {result.rows_skipped:,} | วิเคราะห์ {rebuilt:,} ห้อง"
                    )
                if result.warnings:
                    with st.expander(f"คำเตือน {len(result.warnings)} รายการ"):
                        st.warning("\n".join(result.warnings[:100]))
            except Exception as exc:
                st.error(str(exc))
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        section("รูปแบบข้อมูลที่รองรับ", "ตัวอย่างโครงสร้างพื้นฐานที่ระบบอ่านได้")
        st.code(
            "conversation_id,sender,message,timestamp\n"
            "C001,customer,ขอสอบถามราคาค่ะ,2026-08-01 10:01:00\n"
            "C001,staff,ยินดีค่ะ,2026-08-01 10:03:00"
        )
        insight_card(
            "Smart Parsing",
            "ระบบรองรับชื่อคอลัมน์ใกล้เคียง เช่น room_id / chat_id, role / speaker, text / content, created_at / datetime และรองรับไฟล์แชทที่มี metadata ด้านบนได้",
        )
        insight_card(
            "Import Safely",
            "เมื่ออัปโหลดไฟล์เดิมซ้ำ ระบบจะพยายามตรวจข้อมูลซ้ำและข้าม record เดิม เพื่อไม่ให้แดชบอร์ดบวมโดยไม่จำเป็น",
        )
        st.markdown("</div>", unsafe_allow_html=True)

elif page == "Data Management":
    hero(
        "Data Management",
        "บริหารข้อมูลที่นำเข้า ดูประวัติการอัปโหลด สั่งคำนวณผลวิเคราะห์ใหม่ และ export ข้อมูลออกไปใช้งานต่อได้",
        ["Import History", "Rebuild", "Export CSV"],
    )
    batches = query_df(
        "SELECT batch_id,product_type,source_filename,period_label,imported_at,rows_seen,rows_inserted,rows_skipped,status FROM import_batches ORDER BY imported_at DESC"
    )
    left, right = st.columns([1.5, 1])
    with left:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        section("Import History", "ดูว่าไฟล์ไหนถูกนำเข้าเมื่อไร และมีจำนวน record ที่เพิ่ม/ข้ามเท่าไร")
        st.dataframe(batches, width="stretch", hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        section("Actions", "สำหรับบำรุงรักษาข้อมูลและส่งต่อไปใช้งานภายนอก")
        if st.button("Rebuild Analytics"):
            n = rebuild_analytics(None if product == "ALL" else product)
            st.success(f"คำนวณใหม่ {n:,} ห้อง")
        path = export_conversation_dataset()
        with open(path, "rb") as f:
            st.download_button("ดาวน์โหลด CSV สำหรับ R", f, file_name=path.split("/")[-1], mime="text/csv")
        st.markdown("</div>", unsafe_allow_html=True)
