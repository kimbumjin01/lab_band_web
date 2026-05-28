from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="LAB A팀 합주 관리",
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

MEMBER_COUNT = len(MEMBERS)

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
    if "songs" not in st.session_state:
        st.session_state.songs = []
    if "votes" not in st.session_state:
        st.session_state.votes = {}
    if "next_song_id" not in st.session_state:
        st.session_state.next_song_id = 1
    if "member_availability" not in st.session_state:
        st.session_state.member_availability = {member: {} for member in MEMBERS}
    if "availability" in st.session_state:
        del st.session_state.availability


def slot_key(iso_date: str, time_slot: str) -> str:
    return f"{iso_date}|{time_slot}"


def member_slots(member: str) -> dict:
    if member not in st.session_state.member_availability:
        st.session_state.member_availability[member] = {}
    return st.session_state.member_availability[member]


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


def song_average(song_id: int) -> float | None:
    scores = list(st.session_state.votes.get(song_id, {}).values())
    if not scores:
        return None
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


def build_member_availability_df(start: date, end: date, member: str) -> pd.DataFrame:
    _, columns = date_range_columns(start, end)
    rows = time_slots()
    slots = member_slots(member)
    data = {}

    for col_label in columns:
        iso = st.session_state.schedule_col_iso[col_label]
        data[col_label] = [bool(slots.get(slot_key(iso, slot), False)) for slot in rows]

    return pd.DataFrame(data, index=rows)


def build_availability_summary_df(start: date, end: date) -> pd.DataFrame:
    _, columns = date_range_columns(start, end)
    rows = time_slots()
    data = {}

    for col_label in columns:
        iso = st.session_state.schedule_col_iso[col_label]
        data[col_label] = []
        for slot in rows:
            key = slot_key(iso, slot)
            count = sum(
                1
                for member in MEMBERS
                if member_slots(member).get(key, False)
            )
            data[col_label].append(f"{count}/{MEMBER_COUNT}")

    return pd.DataFrame(data, index=rows)


def save_member_availability_from_df(df: pd.DataFrame, member: str) -> None:
    slots = member_slots(member)
    col_iso = st.session_state.get("schedule_col_iso", {})

    for col_label in df.columns:
        iso = col_iso.get(col_label)
        if not iso:
            continue
        for slot in df.index:
            slots[slot_key(iso, slot)] = bool(df.loc[slot, col_label])


def render_vote_tab() -> None:
    st.subheader("선곡 투표")
    st.caption("곡을 추가하고, 팀원별로 1~5점을 투표해 보세요.")

    with st.expander("곡 추가", expanded=len(st.session_state.songs) == 0):
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
                    song_id = st.session_state.next_song_id
                    st.session_state.next_song_id += 1
                    st.session_state.songs.append(
                        {
                            "id": song_id,
                            "title": title.strip(),
                            "url": youtube_embed_url(youtube_url),
                            "uploaded_by": uploader,
                        }
                    )
                    st.session_state.votes[song_id] = {}
                    st.success(
                        f"{uploader}님이 「{title.strip()}」을(를) 추가했습니다."
                    )
                    st.rerun()

    if not st.session_state.songs:
        st.info("아직 등록된 곡이 없습니다. 위 폼에서 곡을 추가해 주세요.")
        return

    voter = st.selectbox("투표자 (본인 이름)", MEMBERS, key="vote_member")

    st.divider()

    for song in st.session_state.songs:
        song_id = song["id"]
        avg = song_average(song_id)
        vote_count = len(st.session_state.votes.get(song_id, {}))
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
                my_score = st.session_state.votes.get(song_id, {}).get(voter)
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
                    if song_id not in st.session_state.votes:
                        st.session_state.votes[song_id] = {}
                    st.session_state.votes[song_id][voter] = score
                    st.toast(f"{voter}님이 「{song['title']}」에 {score}점 투표!")
                    st.rerun()

                if my_score is not None:
                    st.caption(f"내 투표: {my_score}점 (변경 시 다시 제출)")


def render_schedule_tab() -> None:
    st.subheader("일정 조정")
    st.caption(
        "본인 이름을 선택한 뒤 가능한 시간을 체크하세요. "
        f"아래 요약 표에는 시간대별로 몇 명이 가능한지 ({MEMBER_COUNT}명 기준) 표시됩니다."
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

    summary_df = build_availability_summary_df(start_date, end_date)

    st.markdown("**팀 가능 인원 요약** · 각 칸 = `가능 인원 / 전체`")
    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=False,
    )

    st.divider()

    member_df = build_member_availability_df(start_date, end_date, schedule_member)

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

    save_member_availability_from_df(edited_df, schedule_member)

    my_checked = int(edited_df.values.sum())
    st.caption(
        f"{schedule_member}님이 체크한 칸: {my_checked}개 · "
        "변경 사항은 자동 저장됩니다."
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
            background: linear-gradient(180deg, #1e1b2e 0%, #2d2640 55%, #1a1628 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.06);
        }

        [data-testid="stSidebar"] * {
            color: #e8e4f0 !important;
        }

        [data-testid="stSidebar"] .stRadio > label {
            display: none;
        }

        [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 1.15rem 1.3rem !important;
            margin-bottom: 0.9rem !important;
            font-size: 1.18rem !important;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"]:hover {
            background: rgba(139, 92, 246, 0.2);
            border-color: rgba(167, 139, 250, 0.4);
        }

        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
            gap: 0.35rem;
        }

        h1 {
            font-weight: 700 !important;
            letter-spacing: -0.03em;
            background: linear-gradient(120deg, #1e1b2e 0%, #5b21b6 50%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .sidebar-brand {
            font-size: 2.55rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 0.45rem;
            line-height: 1.15;
            background: linear-gradient(120deg, #fff 20%, #c4b5fd 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .sidebar-tagline {
            font-size: 1.28rem !important;
            color: #c9c5d8 !important;
            margin-bottom: 2rem;
            font-weight: 600;
            line-height: 1.35;
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
        st.markdown('<p class="sidebar-brand">LAB A팀</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="sidebar-tagline">합주 관리 웹서비스</p>',
            unsafe_allow_html=True,
        )
        st.divider()
        selected_menu = st.radio(
            "메뉴",
            MENU_OPTIONS,
            format_func=lambda x: f"{MENU_ICONS[x]}  {x}",
            label_visibility="collapsed",
        )

    st.title("LAB A팀 합주 관리")

    if selected_menu == "선곡 투표":
        render_vote_tab()
    elif selected_menu == "일정 조정":
        render_schedule_tab()
    else:
        render_booking_tab()


if __name__ == "__main__":
    main()
