import json
from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import pandas as pd
import streamlit as st

import db
from schedule_timetable import drag_schedule_timetable

st.set_page_config(
    page_title="LAB A팀 합주 관리",
    page_icon="🎸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 사이드바(왼쪽 메뉴)가 header 안 버튼에 의존하므로 header는 숨기지 않음
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

NAME_PLACEHOLDER = "-- 이름을 선택하세요 --"
MEMBER_OPTIONS = [
    NAME_PLACEHOLDER,
    "김범진",
    "이해진",
    "김해찬",
    "권우현",
    "박연수",
    "박준서",
    "정지원",
    "성민수",
    "유수연",
]
ACTUAL_MEMBERS = [m for m in MEMBER_OPTIONS if m != NAME_PLACEHOLDER]
TEAM_LEADER = "김범진"
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
    if "authenticated_member" not in st.session_state:
        st.session_state.authenticated_member = None
    if "global_user" not in st.session_state:
        st.session_state.global_user = NAME_PLACEHOLDER


def is_member_selected() -> bool:
    return st.session_state.get("global_user", NAME_PLACEHOLDER) != NAME_PLACEHOLDER


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated_member"))


def is_admin() -> bool:
    return st.session_state.get("authenticated_member") == TEAM_LEADER


def authenticated_user() -> str | None:
    return st.session_state.get("authenticated_member")


def can_view_scores() -> bool:
    return is_admin()


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
    return sum(votes.values()) / len(votes)


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


def dates_for_component(start: date, end: date) -> list[dict]:
    dates, _ = date_range_columns(start, end)
    return [{"iso": d.isoformat(), "label": date_column_label(d)} for d in dates]


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
                1
                for member in ACTUAL_MEMBERS
                if all_availability.get(member, {}).get(key, False)
            )
            ratio = min(count / TEAM_SIZE, 1.0)
            display_data[col_label].append(f"{count}/{TEAM_SIZE}")
            ratio_data[col_label].append(ratio)

    return pd.DataFrame(display_data, index=rows), pd.DataFrame(ratio_data, index=rows)


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


def save_slots_to_db(
    member: str, new_slots: dict, old_slots: dict[str, bool]
) -> bool:
    """컴포넌트에서 받은 slots JSON을 Supabase에 배치 저장."""
    rows: list[dict] = []
    for key, available in new_slots.items():
        if "|" not in key:
            continue
        iso, slot_time = key.split("|", 1)
        new_val = bool(available)
        old_val = bool(old_slots.get(key, False))
        if new_val == old_val:
            continue
        rows.append(
            {
                "member": member,
                "slot_date": iso,
                "slot_time": slot_time,
                "available": new_val,
            }
        )
    return db.upsert_availability_batch(rows)


def render_login_required() -> None:
    st.warning("로그인 후 이용할 수 있습니다.")


def render_sidebar_auth() -> None:
    prev_user = st.session_state.get("global_user", NAME_PLACEHOLDER)
    selected = st.selectbox("이름 선택", MEMBER_OPTIONS, key="global_user")

    if selected != prev_user:
        st.session_state.authenticated_member = None

    if is_member_selected():
        password = st.text_input(
            "비밀번호 입력",
            type="password",
            key="pw_input",
            placeholder="비밀번호를 입력하세요",
        )
        if password:
            passwords = dict(st.secrets.get("passwords", {}))
            expected = passwords.get(selected)
            if expected and password == expected:
                st.session_state.authenticated_member = selected
            else:
                st.warning("비밀번호가 올바르지 않습니다.")

    if is_authenticated():
        st.caption(f"로그인: **{st.session_state.authenticated_member}**")


def render_confirmed_schedules_banner() -> None:
    schedules = db.get_confirmed_schedules()
    if not schedules:
        return

    latest = schedules[0]
    date_str = latest["schedule_date"]
    st.success(
        f"📌 **다음 합주:** {date_str}  "
        f"{latest['start_time']} ~ {latest['end_time']}"
        + (f"  · {latest['note']}" if latest.get("note") else "")
    )

    with st.expander(f"전체 확정 일정 보기 ({len(schedules)}건)", expanded=False):
        for s in schedules:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    f"**{s['schedule_date']}**  "
                    f"{s['start_time']} ~ {s['end_time']}"
                    + (f"  · {s.get('note', '')}" if s.get("note") else "")
                )
            with col2:
                if is_admin():
                    if st.button("삭제", key=f"del_sched_{s['id']}"):
                        if db.delete_confirmed_schedule(int(s["id"])):
                            st.cache_data.clear()
                            st.rerun()
        st.divider()


def render_vote_tab() -> None:
    if not is_authenticated():
        render_login_required()
        return

    user = authenticated_user()
    st.subheader("선곡 투표")
    st.caption(f"{user}님, 곡을 추가하고 1~5점으로 투표해 보세요.")

    with st.spinner("곡 목록 불러오는 중..."):
        songs = load_songs()
    if songs is None:
        return

    with st.expander("곡 추가", expanded=len(songs) == 0):
        with st.form("add_song_form", clear_on_submit=True):
            st.caption(f"등록자: **{user}** (상단에서 선택한 이름)")
            title = st.text_input("곡 제목", placeholder="예: 봄날")
            youtube_url = st.text_input(
                "유튜브 링크",
                placeholder="https://www.youtube.com/watch?v=...",
            )
            notes = st.text_area(
                "특이사항/비고",
                placeholder="예: 원키 말고 반키 낮춰서, 일렉 솔로 주의 등",
                max_chars=200,
                height=80,
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
                            user,
                            notes,
                        )
                    if ok:
                        st.success(f"{user}님이 「{title.strip()}」을(를) 추가했습니다.")
                        after_write()

    if not songs:
        st.info("아직 등록된 곡이 없습니다. 위 폼에서 곡을 추가해 주세요.")
        return

    st.divider()
    for song in songs:
        song_id = int(song["id"])
        votes = load_votes(song_id)
        if votes is None:
            continue

        avg = song_average(votes)
        vote_count = len(votes)
        uploader = song.get("uploaded_by", "미상")
        my_score = votes.get(user)

        with st.container(border=True):
            header_col, score_col = st.columns([3, 1])
            with header_col:
                st.markdown(f"### {song['title']}")
                st.caption(f"등록: **{uploader}**")
                if song.get("notes"):
                    st.caption(f"📝 {song['notes']}")
            with score_col:
                if can_view_scores():
                    if avg is not None:
                        st.metric("평균 점수", f"{avg:.1f} / 5", f"{vote_count}명 투표")
                    else:
                        st.metric("평균 점수", "—", "투표 없음")
                else:
                    st.metric("평균 점수", "? / 5", "팀장 로그인 후 공개")

            video_col, vote_col = st.columns([1.1, 1])
            with video_col:
                st.video(song["url"])
            with vote_col:
                default_score = int(my_score) if my_score is not None else 3
                score = st.slider(
                    "점수 (1~5점)",
                    min_value=1,
                    max_value=5,
                    value=default_score,
                    key=f"score_{song_id}_{user}",
                )
                if st.button(
                    "투표하기",
                    key=f"submit_vote_{song_id}",
                    use_container_width=True,
                ):
                    with st.spinner("저장 중..."):
                        ok = db.upsert_vote(song_id, user, score)
                    if ok:
                        st.toast(f"{user}님이 「{song['title']}」에 {score}점 투표!")
                        after_write()
                if my_score is not None:
                    st.caption(f"내 투표: {my_score}점 (변경 시 다시 제출)")


def render_schedule_tab() -> None:
    if not is_authenticated():
        render_login_required()
        return

    user = authenticated_user()
    st.subheader("일정 조정")
    st.caption(
        f"{user}님, 드래그로 가능한 시간을 선택한 뒤 표 하단 **저장하기**를 눌러주세요. "
        f"팀 요약은 아래에서 확인할 수 있습니다 ({TEAM_SIZE}명 기준)."
    )

    today = date.today()
    default_end = today + timedelta(days=27)
    date_range = st.date_input(
        "일정 범위",
        value=(today, default_end),
        min_value=today,
        help="오늘부터 최대 4주(28일) 범위를 기본으로 합니다.",
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range

    if (end_date - start_date).days + 1 > 28:
        st.warning("선택 범위가 28일을 넘습니다. 표가 넓어질 수 있습니다.")

    with st.spinner("내 일정 불러오는 중..."):
        member_slots = load_member_availability(user, start_date, end_date)
    if member_slots is None:
        return

    dates_payload = dates_for_component(start_date, end_date)
    times_payload = time_slots()
    selected_payload = {k: bool(v) for k, v in member_slots.items() if v}

    st.markdown(f"**{user}님의 가능 시간** · 드래그로 선택")

    if not dates_payload:
        st.warning("선택한 일정 범위에 날짜가 없습니다.")
        return

    component_key = f"drag_{user}_{start_date}_{end_date}"
    component_result = drag_schedule_timetable(
        dates=dates_payload,
        times=times_payload,
        selected=selected_payload,
        key=component_key,
    )

    if component_result and component_result.get("action") == "save":
        new_slots = component_result.get("slots", {})
        save_fingerprint = json.dumps(new_slots, sort_keys=True, default=str)
        if st.session_state.get("last_schedule_save") != save_fingerprint:
            with st.spinner(
                "저장 중... 페이지를 닫거나 새로고침하지 마세요. "
                "저장이 끝날 때까지 기다려 주세요."
            ):
                ok = save_slots_to_db(user, new_slots, member_slots)
            if ok:
                st.session_state.last_schedule_save = save_fingerprint
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
    styled_summary = style_availability_summary(summary_display_df, summary_ratio_df)
    st.markdown(
        f"**팀 가능 인원 요약** · 각 칸 = `가능 인원 / {TEAM_SIZE}` "
        "(진할수록 가능 인원 비율이 높음)"
    )
    st.dataframe(styled_summary, use_container_width=True, hide_index=False)

    if is_admin():
        st.divider()
        st.markdown("### 📌 합주 일정 확정")
        with st.form("confirm_schedule_form", clear_on_submit=True):
            sched_date = st.date_input("날짜")
            col1, col2 = st.columns(2)
            with col1:
                start_t = st.selectbox(
                    "시작", [f"{h:02d}:00" for h in range(10, 23)]
                )
            with col2:
                end_t = st.selectbox(
                    "종료", [f"{h:02d}:00" for h in range(11, 24)]
                )
            note_input = st.text_input("비고 (선택)")
            if st.form_submit_button("확정 공지 등록", use_container_width=True):
                if db.add_confirmed_schedule(
                    sched_date.isoformat(), start_t, end_t, note_input
                ):
                    st.cache_data.clear()
                    st.toast("합주 일정이 등록되었습니다!")
                    st.rerun()


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
            visibility: visible !important;
            display: block !important;
            background: linear-gradient(165deg, #14121f 0%, #231f35 42%, #1a1728 100%);
            border-right: 1px solid rgba(167, 139, 250, 0.12);
        }

        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
            display: flex;
            flex-direction: column;
            min-height: calc(100vh - 4rem);
            padding: 0.5rem 0.25rem 1.5rem;
        }

        [data-testid="stSidebar"] * { color: #ece9f5 !important; }
        [data-testid="stSidebar"] hr {
            margin: 1.25rem 0 1.5rem !important;
            border-color: rgba(255, 255, 255, 0.12) !important;
        }

        .sidebar-header-wrap { padding: 0.25rem 0.35rem 0.5rem; }
        .sidebar-brand {
            font-size: clamp(2.35rem, 9vw, 3.4rem) !important;
            font-weight: 800 !important;
            letter-spacing: -0.04em;
            margin: 0 0 0.5rem 0 !important;
            line-height: 1.1 !important;
            background: linear-gradient(125deg, #fff 0%, #ddd6fe 45%, #a78bfa 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .sidebar-tagline {
            font-size: clamp(1.2rem, 4.5vw, 1.65rem) !important;
            color: #c4bfd6 !important;
            margin: 0 !important;
            font-weight: 600 !important;
        }
        .sidebar-menu-label {
            font-size: clamp(1rem, 3.8vw, 1.12rem) !important;
            color: #9b94b0 !important;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 700 !important;
            margin: 0 0 1rem 0.35rem !important;
        }

        [data-testid="stSidebar"] .stRadio { flex: 1; width: 100%; }
        [data-testid="stSidebar"] .stRadio > label { display: none; }
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
            width: 100% !important;
            box-sizing: border-box !important;
            min-height: 3.25rem;
            font-size: clamp(1.2rem, 4.8vw, 1.5rem) !important;
            font-weight: 650 !important;
        }
        [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"]:has(input:checked) {
            background: linear-gradient(135deg, rgba(124,58,237,0.55), rgba(99,102,241,0.4)) !important;
            border-color: rgba(196, 181, 253, 0.65) !important;
        }

        .sidebar-credit-wrap {
            margin-top: auto;
            padding: 2.25rem 0.5rem 0.75rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
        }
        .sidebar-credit {
            font-size: clamp(1rem, 3.8vw, 1.15rem) !important;
            color: #8f879e !important;
            margin: 0 !important;
        }
        .sidebar-credit .credit-name {
            color: #c4b5fd !important;
            font-weight: 700 !important;
        }

        h1 {
            font-weight: 700 !important;
            letter-spacing: -0.03em;
            background: linear-gradient(120deg, #1e1b2e 0%, #5b21b6 50%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        [data-testid="stVideo"] { max-width: 320px; }
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
        render_sidebar_auth()
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
                <p class="sidebar-credit">Made by <span class="credit-name">@kbj110</span></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.title("LAB A팀 합주 관리")
    render_confirmed_schedules_banner()
    st.divider()

    if selected_menu == "선곡 투표":
        render_vote_tab()
    elif selected_menu == "일정 조정":
        render_schedule_tab()
    else:
        render_booking_tab()


if __name__ == "__main__":
    main()
