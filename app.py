import streamlit as st

st.set_page_config(
    page_title="LAB A팀 합주 관리",
    page_icon="🎸",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background: linear-gradient(160deg, #f4f6fb 0%, #eef1f8 45%, #e8ecf4 100%);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1b2e 0%, #2d2640 55%, #1a1628 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }

    [data-testid="stSidebar"] * {
        color: #e8e4f0 !important;
    }

    [data-testid="stSidebar"] .stRadio label {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 0.65rem 1rem;
        margin-bottom: 0.35rem;
        transition: all 0.2s ease;
    }

    [data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(139, 92, 246, 0.18);
        border-color: rgba(167, 139, 250, 0.35);
    }

    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.45), rgba(99, 102, 241, 0.35));
        border-color: rgba(167, 139, 250, 0.6);
        box-shadow: 0 4px 20px rgba(124, 58, 237, 0.25);
    }

    h1 {
        font-weight: 700 !important;
        letter-spacing: -0.03em;
        background: linear-gradient(120deg, #1e1b2e 0%, #5b21b6 50%, #6366f1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .content-card {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.9);
        border-radius: 20px;
        padding: 2.5rem 2rem;
        margin-top: 1rem;
        box-shadow: 0 8px 32px rgba(30, 27, 46, 0.08);
        text-align: center;
    }

    .content-card p {
        color: #64748b;
        font-size: 1.05rem;
        margin: 0;
        letter-spacing: -0.01em;
    }

    .menu-badge {
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #7c3aed;
        background: rgba(124, 58, 237, 0.1);
        padding: 0.35rem 0.85rem;
        border-radius: 999px;
        margin-bottom: 0.75rem;
    }

    .sidebar-brand {
        font-size: 1.35rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 0.25rem;
        background: linear-gradient(120deg, #fff 30%, #c4b5fd 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .sidebar-tagline {
        font-size: 0.8rem;
        color: #a5a3b5 !important;
        margin-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

MENU_OPTIONS = ["선곡 투표", "일정 조정", "합주실 예약"]
MENU_ICONS = {
    "선곡 투표": "🎵",
    "일정 조정": "📅",
    "합주실 예약": "🎹",
}

with st.sidebar:
    st.markdown('<p class="sidebar-brand">LAB A팀</p>', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-tagline">합주 관리 웹서비스</p>', unsafe_allow_html=True)
    st.divider()
    selected_menu = st.radio(
        "메뉴",
        MENU_OPTIONS,
        format_func=lambda x: f"{MENU_ICONS[x]}  {x}",
        label_visibility="collapsed",
    )

st.title("LAB A팀 합주 관리")

st.markdown(
    f"""
    <div class="content-card">
        <span class="menu-badge">{MENU_ICONS[selected_menu]} {selected_menu}</span>
        <p>개발 준비 중입니다.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
