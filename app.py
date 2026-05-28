from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import pandas as pd
import streamlit as st

import db

st.set_page_config(
    page_title="LAB A team 합주 관리",
    page_icon="🎸",
    layout="wide",
    initial_sidebar_state="expanded",
)

MEMBERS = [
    "김범진",
    "이해진",
    "김해찬",
    "권우현",
    "박준서",
    "최주혁",
    "정지원",
    "성민수",
    "유수연",
]

TEAM_SIZE = 7

MENU_OPTIONS = ["선곡 투표", "일정 조정", "합주실 예약"]
MENU_ICONS = {
    "선곡 투표": "🎵",
    "일정 조정": "📅",
    "합주실 예약": "🎹",
}

HOUR_START = 10
HOUR_END = 23
WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

PRACTICE_ROOMS = [
    ("그루브 (사당/방배)", "https://www.groove4.co.kr/"),
    ("길드합주실 (낙성대)", "https://naver.me/FeNycqgi"),
    ("드림합주실 (1호점)", "https://naver.me/xNLZ73gF"),
    ("드림합주실 (2호점)", "https://naver.me/xfYAPtAl"),
]


def init_session_state() -> None:
    if "schedule_col_iso" not in st.session_state:
        st.session_state.schedule_col_iso = {}


def slot_key(iso_date: str, time_slot: str) -> str:
    return f"{iso_date}|{time_slot}"


@st.cache_data(ttl=15)
def load_songs() -> list[dict] | None:
    return db.get_all_songs()


@st.cache_data(ttl=15)
def load_votes(song_id: int) -> dict[str, int] | None:
    return db.get_votes(song_id)


@st.cache_data(ttl=15)
def load_member_availability(
    member: str, start_date: date, end_date: date
) -> dict[str, bool] | None:
    return db.get_member_availability(member, start_date, end_date)


@st.cache_data(ttl=15)
def load_all_availability(
    start_date: date, end_date: date
) -> dict[str, dict[str, bool]] | None:
    return db.get_all_availability(start_date, end_date)


def after_write() -> None:
    st.cache_data.clear()
    st.rerun()


def youtube_embed_url(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().replace("www.", "")

    if host in ("youtu.be",):
        video_id = parsed.path.lstrip("/").split("/")[0]
    elif host in ("youtube.com", "m.youtube.com"):
        if parsed.path.startswith("/shorts/"):
            video_id = parsed.path.split("/")[2]
        else:
            video_id = parse_qs(parsed.query).get("v", [""])[0]
    else:
        return url.strip()

    if not video_id:
        return url.strip()
    return f"https://www.youtube.com/watch?v={video_id}"


def song_average(votes: dict[str, int]) -> float | None:
    if not votes:
        return None
    scores = list(votes.values())
    return sum(scores) / len(scores)


def time_slots() -> list[str]:
    return [f"{hour:02d}:00" for hour in range(HOUR_START, HOUR_END + 1)]


def date_column_label(d: date) -> str:
    weekday = WEEKDAY_KO[d.weekday()]
    return f"{d.month}/{d.day} ({weekday})"


def date_range_columns(start: date, end: date) -> tuple[list[date], list[str]]:
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    columns = [date_column_label(d) for d in dates]
    st.session_state.schedule_col_iso = {
        label: d.isoformat() for label, d in zip(columns, dates)
    }
    return dates, columns


def build_member_availability_df(
    start: date, end: date, member: str, slots: dict[str, bool]
) -> pd.DataFrame:
    _, columns = date_range_columns(start, end)
    rows = time_slots()
    data = {}

    for col_label in columns:
        iso = st.session_state.schedule_col_iso[col_label]
        data[col_label] = [bool(slots.get(slot_key(iso, slot), False)) for slot in rows]

    return pd.DataFrame(data, index=rows)


def build_availability_summary_dfs(
    start: date, end: date, all_availability: dict[str, dict[str, bool]]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    _, columns = date_range_columns(start, end)
    rows = time_slots()
    display_data: dict[str, list[str]] = {}
    ratio_data: dict[str, list[float]] = {}

    for col_label in columns:
        iso = st.session_state.schedule_col_iso[col_label]
        display_data[col_label] = []
        ratio_data[col_label] = []
        for slot in rows:
            key = slot_key(iso, slot)
            count = sum(
                1 for member in MEMBERS if all_availability.get(member, {}).get(key, False)
            )
            ratio = min(count / TEAM_SIZE, 1.0)
            display_data[col_label].append(f"{count}/{TEAM_SIZE}")
            ratio_data[col_label].append(ratio)

    display_df = pd.DataFrame(display_data, index=rows)
    ratio_df = pd.DataFrame(ratio_data, index=rows)
    return display_df, ratio_df


def style_availability_summary(display_df: pd.DataFrame, ratio_df: pd.DataFrame):
    def ratio_cell_style(ratio: float) -> str:
        light = (238, 244, 255)
        dark = (29, 78, 216)
        r = int(light[0] + (dark[0] - light[0]) * ratio)
        g = int(light[1] + (dark[1] - light[1]) * ratio)
        b = int(light[2] + (dark[2] - light[2]) * ratio)
        text = "#ffffff" if ratio >= 0.55 else "#1e293b"
        weight = "700" if ratio >= 0.7 else "600"
        return (
            f"background-color: rgb({r}, {g}, {b}); "
            f"color: {text}; font-weight: {weight}; text-align: center;"
        )

    def style_column(col: pd.Series) -> list[str]:
        col_name = col.name
        return [ratio_cell_style(ratio_df.loc[idx, col_name]) for idx in col.index]

    return display_df.style.apply(style_column, axis=0)


def save_member_availability_from_df(
    edited_df: pd.DataFrame, original_df: pd.DataFrame, member: str
) -> bool:
    col_iso = st.session_state.get("schedule_col_iso", {})
    rows: list[dict] = []

    for col_label in edited_df.columns:
        iso = col_iso.get(col_label)
        if not iso:
            continue
        for slot in edited_df.index:
            new_val = bool(edited_df.loc[slot, col_label])
            old_val = bool(original_df.loc[slot, col_label])
            if new_val == old_val:
                continue
            rows.append(
                {
                    "member": member,
                    "slot_date": iso,
                    "slot_time": slot,
                    "available": new_val,
                }
            )

    return db.upsert_availability_batch(rows)


def render_vote_tab() -> None:
    st.subheader("선곡 투표")
    st.caption("곡을 추가하고, 팀원별로 1~5점을 투표해 보세요.")

    with st.spinner("곡 목록 불러오는 중..."):
        songs = load_songs()

    if songs is None:
        return

    with st.expander("곡 추가", expanded=len(songs) == 0):
        with st.form("add_song_form", clear_on_submit=True):
            uploader = st.selectbox("등록자 (본인 이름)", MEMBERS)
            title = st.text_input("곡 제목", placeholder="예: 봄날")
            youtube_url = st.text_input(
                "유튜브 링크",
                placeholder="https://www.youtube.com/watch?v=...",
            )
            submitted = st.form_submit_button("목록에 추가", use_container_width=True)

            if submitted:
                if not title.strip():
                    st.warning("곡 제목을 입력해 주세요.")
                elif not youtube_url.strip():
                    st.warning("유튜브 링크를 입력해 주세요.")
                else:
                    with st.spinner("저장 중..."):
                        ok = db.add_song(
                            title.strip(),
                            youtube_embed_url(youtube_url),
                            uploader,
                        )
                    if ok:
                        st.success(
                            f"{uploader}님이 「{title.strip()}」을(를) 추가했습니다."
                        )
                        after_write()

    if not songs:
        st.info("아직 등록된 곡이 없습니다. 위 폼에서 곡을 추가해 주세요.")
        return

    voter = st.selectbox("투표자 (본인 이름)", MEMBERS, key="vote_member")

    st.divider()

    for song in songs:
        song_id = int(song["id"])
        votes = load_votes(song_id)
        if votes is None:
            continue

        avg = song_average(votes)
        vote_count = len(votes)
        uploader = song.get("uploaded_by", "미상")

        with st.container(border=True):
            header_col, score_col = st.columns([3, 1])
            with header_col:
                st.markdown(f"### {song['title']}")
                st.caption(f"등록: **{uploader}**")
            with score_col:
                if avg is not None:
                    st.metric("평균 점수", f"{avg:.1f} / 5", f"{vote_count}명 투표")
                else:
                    st.metric("평균 점수", "—", "투표 없음")

            video_col, vote_col = st.columns([1.1, 1])
            with video_col:
                st.video(song["url"])
            with vote_col:
                my_score = votes.get(voter)
                default_score = int(my_score) if my_score is not None else 3

                score = st.slider(
                    "점수 (1~5점)",
                    min_value=1,
                    max_value=5,
                    value=default_score,
                    key=f"score_{song_id}_{voter}",
                )

                if st.button(
                    "투표하기",
                    key=f"submit_vote_{song_id}",
                    use_container_width=True,
                ):
                    with st.spinner("저장 중..."):
                        ok = db.upsert_vote(song_id, voter, score)
                    if ok:
                        st.toast(f"{voter}님이 「{song['title']}」에 {score}점 투표!")
                        after_write()

                if my_score is not None:
                    st.caption(f"내 투표: {my_score}점 (변경 시 다시 제출)")


def render_schedule_tab() -> None:
    st.subheader("일정 조정")
    st.caption(
        "본인 이름을 선택한 뒤 가능한 시간을 체크하고, **일정 저장** 버튼을 눌러주세요. "
        f"맨 아래 팀 요약 표에서 시간대별 가능 인원을 확인할 수 있습니다 ({TEAM_SIZE}명 기준)."
    )

    today = date.today()
    default_end = today + timedelta(days=27)

    date_range = st.date_input(
        "일정 범위",
        value=(today, default_end),
        min_value=today,
        help="오늘부터 최대 4주(28일) 범위를 기본으로 합니다. 필요하면 범위를 조정하세요.",
    )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range

    if (end_date - start_date).days + 1 > 28:
        st.warning("선택 범위가 28일을 넘습니다. 표가 넓어질 수 있습니다.")

    schedule_member = st.selectbox(
        "일정 입력 (본인 이름)",
        MEMBERS,
        key="schedule_member",
    )

    with st.spinner("내 일정 불러오는 중..."):
        member_slots_data = load_member_availability(
            schedule_member, start_date, end_date
        )

    if member_slots_data is None:
        return

    member_df = build_member_availability_df(
        start_date, end_date, schedule_member, member_slots_data
    )

    st.markdown(f"**{schedule_member}님의 가능 시간** · 행 = 시간, 열 = 날짜")
    edited_df = st.data_editor(
        member_df,
        use_container_width=True,
        hide_index=False,
        column_config={
            col: st.column_config.CheckboxColumn(
                col,
                help=f"{col}에 가능하면 체크",
                default=False,
            )
            for col in member_df.columns
        },
        key=f"schedule_editor_{schedule_member}_{start_date}_{end_date}",
    )

    has_changes = not edited_df.astype(bool).equals(member_df.astype(bool))
    my_checked = int(edited_df.values.sum())

    if has_changes:
        changed_count = int((edited_df.astype(bool) != member_df.astype(bool)).values.sum())
        st.warning(f"저장되지 않은 변경 {changed_count}칸이 있습니다. 아래 **일정 저장**을 눌러주세요.")

    save_col, info_col = st.columns([1, 2])
    with save_col:
        save_clicked = st.button(
            "일정 저장",
            type="primary",
            disabled=not has_changes,
            use_container_width=True,
            key=f"save_schedule_{schedule_member}_{start_date}_{end_date}",
        )
    with info_col:
        st.caption(
            f"{schedule_member}님이 체크한 칸: {my_checked}개 · "
            "여러 칸을 연속으로 선택한 뒤 한 번에 저장할 수 있습니다."
        )

    if save_clicked:
        with st.spinner(
            "저장 중... 페이지를 닫거나 새로고침하지 마세요. 저장이 끝날 때까지 기다려 주세요."
        ):
            ok = save_member_availability_from_df(
                edited_df, member_df, schedule_member
            )
        if ok:
            st.success("일정이 저장되었습니다.")
            after_write()

    st.divider()

    with st.spinner("팀 일정 불러오는 중..."):
        all_availability = load_all_availability(start_date, end_date)

    if all_availability is None:
        return

    summary_display_df, summary_ratio_df = build_availability_summary_dfs(
        start_date, end_date, all_availability
    )
    styled_summary = style_availability_summary(
        summary_display_df, summary_ratio_df
    )

    st.markdown(
        f"**팀 가능 인원 요약** · 각 칸 = `가능 인원 / {TEAM_SIZE}` "
        "(진할수록 가능 인원 비율이 높음)"
    )
    st.dataframe(
        styled_summary,
        use_container_width=True,
        hide_index=False,
    )


def render_booking_tab() -> None:
    st.subheader("합주실 예약")
    st.caption("아래 버튼을 눌러 각 합주실 예약 페이지로 이동하세요.")

    for name, url in PRACTICE_ROOMS:
        st.link_button(name, url, use_container_width=True)
        st.markdown("")


def inject_styles() -> None:
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
            background: linear-gradient(
                165deg,
                #14121f 0%,
                #231f35 42%,
                #1a1728 100%
            );
            border-right: 1px solid rgba(167, 139, 250, 0.12);
            box-shadow: 4px 0 32px rgba(15, 12, 30, 0.15);
        }

        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
            display: flex;
            flex-direction: column;
            min-height: calc(100vh - 4rem);
            padding: 0.5rem 0.25rem 1.5rem;
        }

        [data-testid="stSidebar"] * {
            color: #ece9f5 !important;
        }

        [data-testid="stSidebar"] hr {
            margin: 1.25rem 0 1.5rem !important;
            border-color: rgba(255, 255, 255, 0.12) !important;
        }

        .sidebar-header-wrap {
            padding: 0.25rem 0.35rem 0.5rem;
            margin-bottom: 0.25rem;
        }

        .sidebar-brand {
            font-size: clamp(2.35rem, 9vw, 3.4rem) !important;
            font-weight: 800 !important;
            letter-spacing: -0.04em;
            margin: 0 0 0.5rem 0 !important;
            line-height: 1.1 !important;
            background: linear-gradient(125deg, #ffffff 0%, #ddd6fe 45%, #a78bfa 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            filter: drop-shadow(0 2px 12px rgba(167, 139, 250, 0.25));
        }

        .sidebar-tagline {
            font-size: clamp(1.2rem, 4.5vw, 1.65rem) !important;
            color: #c4bfd6 !important;
            margin: 0 !important;
            font-weight: 600 !important;
            line-height: 1.4 !important;
            letter-spacing: -0.02em;
        }

        .sidebar-menu-label {
            font-size: clamp(1rem, 3.8vw, 1.12rem) !important;
            color: #9b94b0 !important;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 700 !important;
            margin: 0 0 1rem 0.35rem !important;
        }

        [data-testid="stSidebar"] .stRadio {
            flex: 1;
            width: 100%;
        }

        [data-testid="stSidebar"] .stRadio > label {
            display: none;
        }

        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
            gap: clamp(0.65rem, 2.5vw, 1rem) !important;
            width: 100% !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: stretch !important;
        }

        [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] {
            background: rgba(255, 255, 255, 0.06);
            border: 1.5px solid rgba(255, 255, 255, 0.12);
            border-radius: 18px;
            padding: clamp(1.05rem, 4vw, 1.45rem) clamp(1.1rem, 4vw, 1.5rem) !important;
            margin-bottom: 0 !important;
            margin-left: 0 !important;
            margin-right: 0 !important;
            width: 100% !important;
            max-width: 100% !important;
            box-sizing: border-box !important;
            display: flex !important;
            align-items: center !important;
            min-height: 3.25rem;
            font-size: clamp(1.2rem, 4.8vw, 1.5rem) !important;
            font-weight: 650 !important;
            line-height: 1.35 !important;
            transition: all 0.22s ease;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
        }

        [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] > div:first-child {
            flex: 1;
            width: 100%;
        }

        [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] > div,
        [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] p,
        [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] span {
            font-size: inherit !important;
            font-weight: inherit !important;
            line-height: inherit !important;
        }

        [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"]:hover {
            background: rgba(139, 92, 246, 0.22);
            border-color: rgba(196, 181, 253, 0.45);
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(124, 58, 237, 0.2);
        }

        [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"]:has(input:checked) {
            background: linear-gradient(
                135deg,
                rgba(124, 58, 237, 0.55) 0%,
                rgba(99, 102, 241, 0.4) 100%
            ) !important;
            border-color: rgba(196, 181, 253, 0.65) !important;
            box-shadow: 0 8px 28px rgba(124, 58, 237, 0.35);
        }

        .sidebar-credit-wrap {
            margin-top: auto;
            padding: 2.25rem 0.5rem 0.25rem;
            margin-bottom: 0.75rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
        }

        .sidebar-credit {
            font-size: clamp(1rem, 3.8vw, 1.15rem) !important;
            color: #8f879e !important;
            margin: 0 !important;
            font-weight: 500 !important;
            line-height: 1.5 !important;
        }

        .sidebar-credit .credit-name {
            color: #c4b5fd !important;
            font-weight: 700 !important;
            letter-spacing: 0.02em;
        }

        h1 {
            font-weight: 700 !important;
            letter-spacing: -0.03em;
            background: linear-gradient(120deg, #1e1b2e 0%, #5b21b6 50%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        [data-testid="stVideo"] {
            max-width: 320px;
        }

        [data-testid="stVideo"] iframe {
            border-radius: 12px;
            box-shadow: 0 6px 24px rgba(30, 27, 46, 0.12);
        }

        .stLinkButton > a {
            padding: 1.1rem 1.25rem !important;
            font-size: 1.08rem !important;
            font-weight: 600 !important;
            border-radius: 14px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    init_session_state()
    inject_styles()

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-header-wrap">
                <p class="sidebar-brand">LAB A team</p>
                <p class="sidebar-tagline">합주 관리 웹서비스</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown('<p class="sidebar-menu-label">MENU</p>', unsafe_allow_html=True)
        selected_menu = st.radio(
            "메뉴",
            MENU_OPTIONS,
            format_func=lambda x: f"{MENU_ICONS[x]}  {x}",
            label_visibility="collapsed",
        )
        st.markdown(
            """
            <div class="sidebar-credit-wrap">
                <p class="sidebar-credit">
                    Made by <span class="credit-name">@kbj110</span>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.title("LAB A team 합주 관리")

    if selected_menu == "선곡 투표":
        render_vote_tab()
    elif selected_menu == "일정 조정":
        render_schedule_tab()
    else:
        render_booking_tab()


if __name__ == "__main__":
    main()
