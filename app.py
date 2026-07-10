import re
from datetime import date, datetime, timedelta, timezone
from html import escape
from urllib.parse import parse_qs, urlparse

import streamlit as st

import db
from availability_table import availability_summary_table
from schedule_timetable import drag_schedule_timetable
from schedule_logic import (
    availability_rows_for_save,
    schedule_save_fingerprint,
    slot_key as normalized_slot_key,
)

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
CORE_MEMBERS = [
    "김범진",
    "이해진",
    "김해찬",
    "권우현",
    "박연수",
    "박준서",
    "정지원",
]
GUEST_USER = "Guest"
MEMBER_OPTIONS = [NAME_PLACEHOLDER, *CORE_MEMBERS, GUEST_USER]
ACTUAL_MEMBERS = CORE_MEMBERS
TEAM_LEADER = "김범진"
TEAM_SIZE = len(CORE_MEMBERS)
KST = timezone(timedelta(hours=9), "KST")

MENU_OPTIONS = ["홈", "선곡 투표", "일정 조정", "합주실 예약"]
MENU_ICONS = {
    "홈": "🏠",
    "선곡 투표": "🎵",
    "일정 조정": "📅",
    "합주실 예약": "🎹",
}
MENU_THEMES = {
    "홈": {
        "label": "HOME",
        "accent": "#7c3aed",
        "accent_soft": "rgba(124, 58, 237, 0.12)",
    },
    "선곡 투표": {
        "label": "SONG",
        "accent": "#f43f5e",
        "accent_soft": "rgba(244, 63, 94, 0.12)",
    },
    "일정 조정": {
        "label": "TIME",
        "accent": "#2563eb",
        "accent_soft": "rgba(37, 99, 235, 0.12)",
    },
    "합주실 예약": {
        "label": "ROOM",
        "accent": "#059669",
        "accent_soft": "rgba(5, 150, 105, 0.12)",
    },
}

HOUR_START = 13
HOUR_END = 23
WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

PRACTICE_ROOMS = [
    ("그루브 (사당/방배)", "https://www.groove4.co.kr/"),
    ("길드합주실 (낙성대)", "https://naver.me/FeNycqgi"),
    ("드림합주실 (1호점)", "https://naver.me/xNLZ73gF"),
    ("드림합주실 (2호점)", "https://naver.me/xfYAPtAl"),
]

SONGS_PER_PAGE = 10

def init_session_state() -> None:
    if "schedule_col_iso" not in st.session_state:
        st.session_state.schedule_col_iso = {}
    if "authenticated_member" not in st.session_state:
        st.session_state.authenticated_member = None
    if "global_user" not in st.session_state:
        st.session_state.global_user = NAME_PLACEHOLDER
    if "last_selected_user" not in st.session_state:
        st.session_state.last_selected_user = NAME_PLACEHOLDER
    if "vote_page" not in st.session_state:
        st.session_state.vote_page = 0
    if "selected_availability_slot" not in st.session_state:
        st.session_state.selected_availability_slot = None
    if "selected_menu" not in st.session_state:
        st.session_state.selected_menu = MENU_OPTIONS[0]
    elif st.session_state.selected_menu not in MENU_OPTIONS:
        st.session_state.selected_menu = MENU_OPTIONS[0]
    if "song_filter" not in st.session_state:
        st.session_state.song_filter = "전체"
    if "song_sort" not in st.session_state:
        st.session_state.song_sort = "최신순"
    if "login_user" not in st.session_state:
        st.session_state.login_user = NAME_PLACEHOLDER


def is_member_selected() -> bool:
    return st.session_state.get("global_user", NAME_PLACEHOLDER) != NAME_PLACEHOLDER


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated_member"))


def is_guest() -> bool:
    return st.session_state.get("authenticated_member") == GUEST_USER


def is_admin() -> bool:
    return st.session_state.get("authenticated_member") == TEAM_LEADER


def can_write() -> bool:
    return is_authenticated() and not is_guest()


def authenticated_user() -> str | None:
    return st.session_state.get("authenticated_member")


def can_view_scores() -> bool:
    return is_admin()


def role_name() -> str | None:
    if not is_authenticated():
        return None
    return role_for_member(authenticated_user() or "")


def role_for_member(member: str) -> str:
    if member == TEAM_LEADER:
        return "Admin"
    if member == GUEST_USER:
        return "Guest"
    return "Member"


def render_role_badge() -> None:
    role = role_name()
    if not role:
        return

    user = authenticated_user() or ""
    st.markdown(
        f"""
        <div class="role-badge role-{role.lower()}">
            <span>{escape(role)}</span>
            <strong>{escape(user)}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(menu: str, title: str, subtitle: str) -> None:
    theme = MENU_THEMES[menu]
    st.markdown(
        f"""
        <div class="section-header"
             style="--section-accent:{theme['accent']};
                    --section-accent-soft:{theme['accent_soft']};">
            <span class="section-kicker">{escape(theme['label'])}</span>
            <div>
                <h2>{escape(title)}</h2>
                <p>{escape(subtitle)}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_song_header(song: dict, uploader: str) -> None:
    notes = str(song.get("notes") or "").strip()
    notes_html = (
        f"<p class='song-note'>{escape(notes)}</p>"
        if notes
        else ""
    )
    st.markdown(
        f"""
        <div class="song-head">
            <span class="song-tag">TRACK</span>
            <h3>{escape(str(song.get("title", "")))}</h3>
            <p class="song-meta">등록 {escape(str(uploader))}</p>
            {notes_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_comment(member: str, created_at: str, content: str) -> None:
    safe_content = escape(content).replace("\n", "<br>")
    st.markdown(
        f"""
        <div class="comment-row">
            <div>
                <strong>{escape(member)}</strong>
                <span>{escape(created_at[:10])}</span>
            </div>
            <p>{safe_content}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_card(
    label: str,
    value: str,
    caption: str,
    accent: str = "#7c3aed",
) -> None:
    st.markdown(
        f"""
        <div class="dashboard-card" style="--dash-accent:{accent};">
            <span>{escape(label)}</span>
            <strong>{escape(value)}</strong>
            <p>{escape(caption)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_menu() -> str:
    selected = st.session_state.get("selected_menu", MENU_OPTIONS[0])
    if selected not in MENU_OPTIONS:
        selected = MENU_OPTIONS[0]
        st.session_state.selected_menu = selected
    for option in MENU_OPTIONS:
        clicked = st.button(
            f"{MENU_ICONS[option]}  {option}",
            key=f"sidebar_menu_{option}",
            type="primary" if option == selected else "secondary",
            use_container_width=True,
        )
        if clicked:
            selected = option
            st.session_state.selected_menu = option
    return selected


def header_value(headers: object, name: str) -> str:
    for key in (name, name.lower(), name.upper(), name.title()):
        try:
            value = headers.get(key)  # type: ignore[attr-defined]
        except Exception:
            value = None
        if value:
            return str(value)
    return ""


def context_value(name: str) -> str:
    context = getattr(st, "context", None)
    if context is None:
        return ""
    value = getattr(context, name, "")
    return "" if value is None else str(value)


def request_headers() -> object:
    context = getattr(st, "context", None)
    if context is None:
        return {}
    return getattr(context, "headers", {}) or {}


def version_from_user_agent(pattern: str, user_agent: str) -> str:
    match = re.search(pattern, user_agent, re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).replace("_", ".")


def parse_user_agent(user_agent: str) -> dict[str, str]:
    ua = user_agent or ""
    lower = ua.lower()

    browser = "Unknown"
    browser_version = ""
    browser_patterns = [
        ("Whale", r"Whale/([\d.]+)"),
        ("Samsung Internet", r"SamsungBrowser/([\d.]+)"),
        ("Edge", r"EdgA?/([\d.]+)"),
        ("Opera", r"(?:OPR|Opera)/([\d.]+)"),
        ("Chrome iOS", r"CriOS/([\d.]+)"),
        ("Firefox iOS", r"FxiOS/([\d.]+)"),
        ("Chrome", r"Chrome/([\d.]+)"),
        ("Firefox", r"Firefox/([\d.]+)"),
        ("Safari", r"Version/([\d.]+).*Safari"),
    ]
    for name, pattern in browser_patterns:
        version = version_from_user_agent(pattern, ua)
        if version:
            browser = name
            browser_version = version
            break

    os_name = "Unknown"
    os_version = ""
    if "iphone" in lower:
        os_name = "iOS"
        os_version = version_from_user_agent(r"iPhone OS ([\d_]+)", ua)
    elif "ipad" in lower:
        os_name = "iPadOS"
        os_version = version_from_user_agent(r"CPU OS ([\d_]+)", ua)
    elif "android" in lower:
        os_name = "Android"
        os_version = version_from_user_agent(r"Android ([\d.]+)", ua)
    elif "cros" in lower:
        os_name = "ChromeOS"
        os_version = version_from_user_agent(r"CrOS [^ ]+ ([\d.]+)", ua)
    elif "windows" in lower:
        os_name = "Windows"
        os_version = version_from_user_agent(r"Windows NT ([\d.]+)", ua)
    elif "mac os x" in lower:
        os_name = "macOS"
        os_version = version_from_user_agent(r"Mac OS X ([\d_]+)", ua)
    elif "linux" in lower:
        os_name = "Linux"

    if "ipad" in lower or "tablet" in lower or ("android" in lower and "mobile" not in lower):
        device_type = "tablet"
    elif "mobi" in lower or "iphone" in lower or "ipod" in lower:
        device_type = "mobile"
    elif ua:
        device_type = "desktop"
    else:
        device_type = "unknown"

    device_detail = "Unknown"
    if "iphone" in lower:
        device_detail = "iPhone"
    elif "ipad" in lower:
        device_detail = "iPad"
    elif "ipod" in lower:
        device_detail = "iPod"
    elif "android" in lower:
        model = re.search(r"Android [^;)]*;\s*([^;)]+)", ua, re.IGNORECASE)
        device_detail = model.group(1).strip() if model else "Android device"
    elif "windows" in lower:
        device_detail = "Windows PC"
    elif "macintosh" in lower:
        device_detail = "Mac"
    elif "cros" in lower:
        device_detail = "ChromeOS device"
    elif "linux" in lower:
        device_detail = "Linux device"

    return {
        "browser": browser,
        "browser_version": browser_version,
        "os": os_name,
        "os_version": os_version,
        "device_type": device_type,
        "device_detail": device_detail,
    }


def build_access_log(member: str) -> dict[str, str]:
    headers = request_headers()
    user_agent = header_value(headers, "user-agent")
    parsed = parse_user_agent(user_agent)
    forwarded_for = header_value(headers, "x-forwarded-for")

    return {
        "event_type": "login_success",
        "member": member,
        "role": role_for_member(member),
        "login_at_kst": datetime.now(KST).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S"),
        "ip_address": context_value("ip_address") or forwarded_for.split(",")[0].strip(),
        "forwarded_for": forwarded_for,
        "user_agent": user_agent,
        "browser": parsed["browser"],
        "browser_version": parsed["browser_version"],
        "os": parsed["os"],
        "os_version": parsed["os_version"],
        "device_type": parsed["device_type"],
        "device_detail": parsed["device_detail"],
        "locale": context_value("locale"),
        "browser_timezone": context_value("timezone"),
        "accept_language": header_value(headers, "accept-language"),
        "app_url": context_value("url"),
        "referrer": header_value(headers, "referer") or header_value(headers, "referrer"),
    }


def log_login_success(member: str) -> None:
    db.add_access_log(build_access_log(member))


def prewarm_app_cache() -> None:
    """로그인 전 대기 시간에 자주 쓰는 데이터를 캐시에 올린다."""
    today = date.today()
    default_end = today + timedelta(days=27)
    db.get_confirmed_schedules()
    load_songs()
    load_all_votes()
    load_all_comments()
    load_all_availability(today, default_end)


def authenticate_member(selected: str, password: str) -> bool:
    passwords = dict(st.secrets.get("passwords", {}))
    expected = passwords.get(selected)
    if expected and password == expected:
        st.session_state.authenticated_member = selected
        st.session_state.global_user = selected
        st.session_state.last_selected_user = selected
        st.session_state.selected_menu = "홈"
        log_login_success(selected)
        return True
    return False


def authenticate_guest() -> None:
    st.session_state.authenticated_member = GUEST_USER
    st.session_state.global_user = GUEST_USER
    st.session_state.last_selected_user = GUEST_USER
    st.session_state.selected_menu = "홈"
    log_login_success(GUEST_USER)


def render_login_page() -> None:
    st.markdown(
        """
        <div class="login-shell">
            <div class="login-card">
                <span class="login-kicker">LAB A TEAM</span>
                <h1>합주 관리 로그인</h1>
                <p>팀원은 비밀번호로 로그인하고, Guest는 보기 전용으로 접속할 수 있습니다.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.1, 0.9])
    with left:
        with st.form("login_form"):
            selected = st.selectbox(
                "이름 선택",
                [NAME_PLACEHOLDER, *CORE_MEMBERS],
                key="login_user",
            )
            password = st.text_input(
                "비밀번호 입력",
                type="password",
                placeholder="비밀번호를 입력하세요",
            )
            submitted = st.form_submit_button("로그인", use_container_width=True)
            if submitted:
                if selected == NAME_PLACEHOLDER:
                    st.warning("이름을 먼저 선택해 주세요.")
                elif authenticate_member(selected, password):
                    st.rerun()
                else:
                    st.warning("비밀번호가 올바르지 않습니다.")

    with right:
        st.markdown(
            """
            <div class="guest-panel">
                <strong>Guest</strong>
                <p>선곡, 댓글, 팀 가능 인원 요약을 보기 전용으로 확인합니다.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Guest로 보기", use_container_width=True):
            authenticate_guest()
            st.rerun()

    with st.spinner("앱 데이터를 미리 준비하는 중..."):
        prewarm_app_cache()


def slot_key(iso_date: str, time_slot: str) -> str:
    return normalized_slot_key(iso_date, time_slot)


@st.cache_data(ttl=15)
def load_songs() -> list[dict] | None:
    return db.get_all_songs()


@st.cache_data(ttl=15)
def load_all_votes() -> dict[int, dict[str, int]] | None:
    return db.get_all_votes()


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

@st.cache_data(ttl=15)
def load_all_comments() -> dict[int, list[dict]] | None:
    return db.get_all_comments()


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


def core_votes(votes: dict[str, int]) -> dict[str, int]:
    return {
        member: int(score)
        for member, score in votes.items()
        if member in CORE_MEMBERS
    }


def missing_voters(votes: dict[str, int]) -> list[str]:
    scored = core_votes(votes)
    return [member for member in CORE_MEMBERS if member not in scored]


def song_average_core(votes: dict[str, int]) -> float | None:
    return song_average(core_votes(votes))


def vote_count_core(votes: dict[str, int]) -> int:
    return len(core_votes(votes))


def sort_score_value(song: dict, all_votes: dict[int, dict[str, int]], user: str) -> int:
    votes = all_votes.get(int(song["id"]), {})
    score = votes.get(user)
    return int(score) if score is not None else -1


def filter_and_sort_songs(
    songs: list[dict],
    all_votes: dict[int, dict[str, int]],
    all_comments: dict[int, list[dict]],
    user: str,
    filter_mode: str,
    sort_mode: str,
) -> list[dict]:
    filtered = list(songs)

    if filter_mode == "내가 미투표":
        filtered = [
            song for song in filtered
            if user not in all_votes.get(int(song["id"]), {})
        ]
    elif filter_mode == "내가 투표한 곡":
        filtered = [
            song for song in filtered
            if user in all_votes.get(int(song["id"]), {})
        ]
    elif filter_mode == "댓글 있는 곡":
        filtered = [
            song for song in filtered
            if all_comments.get(int(song["id"]), [])
        ]

    if sort_mode == "제목순":
        filtered.sort(key=lambda song: str(song.get("title", "")).lower())
    elif sort_mode == "내 점수 높은순":
        filtered.sort(
            key=lambda song: (
                sort_score_value(song, all_votes, user),
                str(song.get("created_at", "")),
            ),
            reverse=True,
        )
    elif sort_mode == "내 점수 낮은순":
        filtered.sort(
            key=lambda song: (
                sort_score_value(song, all_votes, user) < 0,
                sort_score_value(song, all_votes, user),
                str(song.get("created_at", "")),
            )
        )
    elif sort_mode == "평균 점수 높은순":
        filtered.sort(
            key=lambda song: (
                song_average_core(all_votes.get(int(song["id"]), {})) is not None,
                song_average_core(all_votes.get(int(song["id"]), {})) or 0,
                vote_count_core(all_votes.get(int(song["id"]), {})),
            ),
            reverse=True,
        )
    elif sort_mode == "평균 점수 낮은순":
        filtered.sort(
            key=lambda song: (
                song_average_core(all_votes.get(int(song["id"]), {})) is None,
                song_average_core(all_votes.get(int(song["id"]), {})) or 0,
            )
        )
    elif sort_mode == "투표 적은순":
        filtered.sort(
            key=lambda song: (
                vote_count_core(all_votes.get(int(song["id"]), {})),
                str(song.get("created_at", "")),
            )
        )
    else:
        filtered.sort(key=lambda song: str(song.get("created_at", "")), reverse=True)

    return filtered


def top_availability_slots(
    start: date,
    end: date,
    all_availability: dict[str, dict[str, bool]],
    limit: int = 3,
) -> list[dict]:
    candidates: list[dict] = []
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    for d in days:
        iso = d.isoformat()
        for slot in time_slots():
            key = slot_key(iso, slot)
            members = [
                member for member in CORE_MEMBERS
                if all_availability.get(member, {}).get(key, False)
            ]
            if members:
                candidates.append(
                    {
                        "date": d,
                        "label": date_column_label(d),
                        "time": slot,
                        "count": len(members),
                        "members": members,
                    }
                )

    candidates.sort(key=lambda item: (-item["count"], item["date"], item["time"]))
    return candidates[:limit]


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


def save_slots_to_db(
    member: str, new_slots: dict, old_slots: dict[str, bool]
) -> bool:
    """컴포넌트에서 받은 slots JSON을 Supabase에 배치 저장."""
    rows = availability_rows_for_save(member, new_slots, old_slots)
    return db.upsert_availability_batch(rows)


def render_login_required() -> None:
    st.warning("로그인 후 이용할 수 있습니다.")


def render_sidebar_auth() -> None:
    prev_user = st.session_state.get("last_selected_user", NAME_PLACEHOLDER)
    prev_auth = st.session_state.get("authenticated_member")
    selected = st.selectbox("이름 선택", MEMBER_OPTIONS, key="global_user")

    if selected != prev_user:
        st.session_state.authenticated_member = None
        st.session_state.pw_input = ""
        st.session_state.last_selected_user = selected
        st.session_state.pop("last_schedule_save", None)

    if selected == GUEST_USER:
        if prev_auth != GUEST_USER:
            log_login_success(GUEST_USER)
        st.session_state.authenticated_member = GUEST_USER
        st.caption("Guest는 비밀번호 없이 보기 전용으로 접속합니다.")
    elif selected == NAME_PLACEHOLDER:
        st.caption("팀원은 비밀번호로 로그인하고, Guest는 보기 전용입니다.")
    else:
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
                if st.session_state.get("authenticated_member") != selected:
                    log_login_success(selected)
                st.session_state.authenticated_member = selected
            else:
                st.session_state.authenticated_member = None
                st.warning("비밀번호가 올바르지 않습니다.")

    render_role_badge()


def render_confirmed_schedules_banner() -> None:
    schedules = db.get_confirmed_schedules()
    if not schedules:
        return

    latest = schedules[0]
    date_str = latest["schedule_date"]
    note = str(latest.get("note") or "").strip()
    note_html = (
        f"<span class='schedule-note'>{escape(note)}</span>"
        if note
        else ""
    )
    st.markdown(
        f"""
        <div class="schedule-banner">
            <div class="schedule-pin">📌</div>
            <div class="schedule-copy">
                <span>다음 합주</span>
                <strong>{escape(str(date_str))}</strong>
            </div>
            <div class="schedule-time">{escape(str(latest['start_time']))} ~ {escape(str(latest['end_time']))}</div>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander(f"전체 확정 일정 보기 ({len(schedules)}건)", expanded=False):
        for s in schedules:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    f"""
                    <div class="schedule-list-row">
                        <strong>{escape(str(s['schedule_date']))}</strong>
                        <span>{escape(str(s['start_time']))} ~ {escape(str(s['end_time']))}</span>
                        {f"<em>{escape(str(s.get('note', '')))}</em>" if s.get("note") else ""}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col2:
                if is_admin():
                    if st.button("삭제", key=f"del_sched_{s['id']}"):
                        if db.delete_confirmed_schedule(int(s["id"])):
                            st.cache_data.clear()
                            st.rerun()
        st.divider()


def render_home_tab() -> None:
    if not is_authenticated():
        render_login_required()
        return

    user = authenticated_user() or ""
    if is_guest():
        subtitle = "Guest 보기 전용으로 팀 운영 현황을 빠르게 확인합니다."
    elif is_admin():
        subtitle = "팀장 관점에서 투표와 일정 입력 현황을 한눈에 확인합니다."
    else:
        subtitle = f"{user}님이 아직 해야 할 투표와 일정 입력 상태를 확인합니다."
    render_section_header("홈", "홈", subtitle)

    today = date.today()
    default_end = today + timedelta(days=27)

    with st.spinner("대시보드 불러오는 중..."):
        schedules = db.get_confirmed_schedules() or []
        songs = load_songs() or []
        all_availability = load_all_availability(today, default_end) or {}
        all_votes = (load_all_votes() or {}) if can_write() or is_admin() else {}

    latest = schedules[0] if schedules else None
    if latest:
        next_value = str(latest["schedule_date"])
        next_caption = f"{latest['start_time']} ~ {latest['end_time']}"
    else:
        next_value = "미정"
        next_caption = "확정된 합주 일정이 없습니다."

    cols = st.columns(4)
    with cols[0]:
        render_dashboard_card("다음 합주", next_value, next_caption, "#059669")
    with cols[1]:
        render_dashboard_card("등록 곡", f"{len(songs)}곡", "선곡 투표 후보", "#f43f5e")

    if can_write():
        voted_count = sum(
            1 for song in songs
            if user in all_votes.get(int(song["id"]), {})
        )
        pending_count = max(len(songs) - voted_count, 0)
        with cols[2]:
            render_dashboard_card(
                "내 투표",
                f"{voted_count}/{len(songs)}",
                f"미투표 {pending_count}곡",
                "#7c3aed",
            )
        member_slots = load_member_availability(user, today, default_end) or {}
        selected_slots = sum(1 for value in member_slots.values() if value)
        with cols[3]:
            render_dashboard_card(
                "내 일정",
                f"{selected_slots}칸",
                "최근 4주 가능 시간",
                "#2563eb",
            )
    else:
        with cols[2]:
            render_dashboard_card("권한", "Guest", "보기 전용 접속", "#059669")
        with cols[3]:
            render_dashboard_card("팀 기준", f"{TEAM_SIZE}명", "핵심 참여 멤버", "#2563eb")

    st.divider()
    recs = top_availability_slots(today, default_end, all_availability, limit=3)
    st.markdown("### 추천 가능 시간")
    if recs:
        rec_cols = st.columns(len(recs))
        for idx, rec in enumerate(recs):
            with rec_cols[idx]:
                render_dashboard_card(
                    f"TOP {idx + 1}",
                    f"{rec['label']} {rec['time']}",
                    f"{rec['count']}/{TEAM_SIZE}명 가능",
                    "#2563eb",
                )
    else:
        st.info("아직 추천할 수 있는 팀 가능 시간이 없습니다.")

    if is_admin() and songs:
        st.divider()
        st.markdown("### 팀장 요약")
        admin_left, admin_right = st.columns(2)
        ranked = []
        for song in songs:
            sid = int(song["id"])
            votes = all_votes.get(sid, {})
            avg = song_average_core(votes)
            if avg is not None:
                ranked.append((avg, vote_count_core(votes), song))
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)

        with admin_left:
            with st.container(border=True):
                st.markdown("**평균 상위 곡 TOP 20**")
                if ranked:
                    for idx, (avg, vote_count, song) in enumerate(ranked[:20], start=1):
                        st.markdown(
                            f"{idx}. **{song['title']}** · {avg:.2f}/5 · {vote_count}명"
                        )
                else:
                    st.caption("아직 투표된 곡이 없습니다.")

        missing_by_member = {member: 0 for member in CORE_MEMBERS}
        for song in songs:
            votes = all_votes.get(int(song["id"]), {})
            for member in missing_voters(votes):
                missing_by_member[member] += 1
        with admin_right:
            with st.container(border=True):
                st.markdown("**미투표 요약**")
                for member, count in sorted(
                    missing_by_member.items(),
                    key=lambda item: (-item[1], item[0]),
                ):
                    st.markdown(f"- {member}: {count}곡")


def render_vote_tab() -> None:
    if not is_authenticated():
        render_login_required()
        return

    user = authenticated_user()
    if is_guest():
        subtitle = "등록된 곡과 의견을 보기 전용으로 확인할 수 있습니다."
    else:
        subtitle = f"{user}님, 곡을 추가하고 1~5점으로 투표해 보세요."
    render_section_header("선곡 투표", "선곡 투표", subtitle)

    with st.spinner("곡 목록 불러오는 중..."):
        songs = load_songs()
    if songs is None:
        return

    if can_write():
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
                            st.success(
                                f"{user}님이 「{title.strip()}」을(를) 추가했습니다."
                            )
                            st.session_state.vote_page = 0
                            after_write()

    if not songs:
        if can_write():
            st.info("아직 등록된 곡이 없습니다. 위 폼에서 곡을 추가해 주세요.")
        else:
            st.info("아직 등록된 곡이 없습니다.")
        return

    # ── 배치 로딩 ──
    with st.spinner("데이터 불러오는 중..."):
        should_load_votes = can_write() or can_view_scores()
        all_votes = (load_all_votes() or {}) if should_load_votes else {}
        all_comments = load_all_comments() or {}

    filter_options = ["전체", "댓글 있는 곡"]
    if can_write():
        filter_options = ["전체", "내가 미투표", "내가 투표한 곡", "댓글 있는 곡"]
    sort_options = ["최신순", "제목순"]
    if can_write():
        sort_options.extend(["내 점수 높은순", "내 점수 낮은순"])
    if is_admin():
        sort_options.extend(["평균 점수 높은순", "평균 점수 낮은순", "투표 적은순"])

    if st.session_state.song_filter not in filter_options:
        st.session_state.song_filter = "전체"
    if st.session_state.song_sort not in sort_options:
        st.session_state.song_sort = "최신순"

    control_left, control_right = st.columns(2)
    with control_left:
        filter_mode = st.selectbox(
            "보기 필터",
            filter_options,
            key="song_filter",
        )
    with control_right:
        sort_mode = st.selectbox(
            "정렬",
            sort_options,
            key="song_sort",
        )

    display_songs = filter_and_sort_songs(
        songs,
        all_votes,
        all_comments,
        user or "",
        filter_mode,
        sort_mode,
    )

    # ── 페이지네이션 ──
    total = len(display_songs)
    total_pages = max(1, (total + SONGS_PER_PAGE - 1) // SONGS_PER_PAGE)
    page = min(st.session_state.vote_page, total_pages - 1)
    st.session_state.vote_page = page
    page_songs = display_songs[page * SONGS_PER_PAGE : (page + 1) * SONGS_PER_PAGE]

    st.divider()

    # 페이지 네비게이션 (상단)
    nav_left, nav_mid, nav_right = st.columns([1, 2, 1])
    with nav_left:
        if st.button("◀ 이전", disabled=(page == 0), use_container_width=True):
            st.session_state.vote_page -= 1
            st.rerun()
    with nav_mid:
        st.markdown(
            f"<p style='text-align:center;font-weight:600;'>"
            f"{page + 1} / {total_pages} 페이지 &nbsp;·&nbsp; 표시 {total}곡"
            f" &nbsp;·&nbsp; 전체 {len(songs)}곡"
            f"</p>",
            unsafe_allow_html=True,
        )
    with nav_right:
        if st.button("다음 ▶", disabled=(page >= total_pages - 1), use_container_width=True):
            st.session_state.vote_page += 1
            st.rerun()

    st.divider()

    if not page_songs:
        st.info("현재 필터 조건에 맞는 곡이 없습니다.")
        return

    for song in page_songs:
        song_id = int(song["id"])
        raw_votes = all_votes.get(song_id, {})
        votes = core_votes(raw_votes)
        comments = all_comments.get(song_id, [])

        avg = song_average_core(raw_votes)
        vote_count = vote_count_core(raw_votes)
        missing = missing_voters(raw_votes)
        uploader = song.get("uploaded_by", "미상")
        my_score = raw_votes.get(user)

        with st.container(border=True):
            header_col, score_col = st.columns([3, 1])
            with header_col:
                render_song_header(song, uploader)
            with score_col:
                if can_view_scores():
                    if avg is not None:
                        st.metric("평균 점수", f"{avg:.2f} / 5", f"{vote_count}명 투표")
                    else:
                        st.metric("평균 점수", "—", "투표 없음")
                    if missing:
                        st.caption(f"미투표 {len(missing)}명: {', '.join(missing)}")
                    else:
                        st.caption("전원 투표 완료")
                else:
                    st.metric("평균 점수", "? / 5", "팀장 로그인 후 공개")

            video_col, vote_col = st.columns([1.1, 1])
            with video_col:
                st.video(song["url"])
            with vote_col:
                if can_write():
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
                else:
                    st.info("Guest는 투표할 수 없습니다.")

            # ── 댓글 ──
            st.markdown("💬 **의견**")
            if comments:
                for c in comments:
                    c_col, d_col = st.columns([6, 1])
                    with c_col:
                        display_name = "나" if c["member"] == user else (c["member"] if is_admin() else "익명")
                        render_comment(
                            display_name,
                            str(c.get("created_at", "")),
                            str(c.get("content", "")),
                        )
                    with d_col:
                        if can_write() and c["member"] == user:
                            if st.button(
                                "🗑️",
                                key=f"del_comment_{c['id']}",
                                help="댓글 삭제",
                            ):
                                db.delete_comment(int(c["id"]))
                                after_write()
                st.divider()
            else:
                if can_write():
                    st.caption("아직 의견이 없습니다. 첫 번째로 남겨보세요!")
                else:
                    st.caption("아직 의견이 없습니다.")

            if can_write():
                with st.expander("의견 남기기", expanded=False):
                    with st.form(key=f"comment_form_{song_id}", clear_on_submit=True):
                        new_comment = st.text_area(
                            "의견 작성",
                            placeholder="이 곡에 대한 의견을 자유롭게 남겨주세요.",
                            max_chars=300,
                            height=80,
                            label_visibility="collapsed",
                        )
                        if st.form_submit_button("등록", use_container_width=True):
                            if not new_comment.strip():
                                st.warning("내용을 입력해 주세요.")
                            else:
                                ok = db.add_comment(song_id, user, new_comment)
                                if ok:
                                    st.toast("의견이 등록되었습니다!")
                                    after_write()
            else:
                st.caption("Guest는 의견을 작성할 수 없습니다.")

            if is_admin():
                with st.expander("투표 상세 보기", expanded=False):
                    if votes:
                        st.markdown("**투표자**")
                        for member in CORE_MEMBERS:
                            if member in votes:
                                st.markdown(f"- {member}: {votes[member]}점")
                    else:
                        st.caption("아직 투표한 멤버가 없습니다.")
                    if missing:
                        st.markdown(f"**미투표:** {', '.join(missing)}")
                    else:
                        st.markdown("**미투표:** 없음")

            # ── 본인 곡 수정/삭제 ──
            if can_write() and uploader == user:
                with st.expander("✏️ 내 곡 수정 / 삭제", expanded=False):
                    with st.form(key=f"edit_song_{song_id}"):
                        new_title = st.text_input(
                            "곡 제목",
                            value=song["title"],
                            key=f"edit_title_{song_id}",
                        )
                        new_notes = st.text_area(
                            "특이사항/비고",
                            value=song.get("notes") or "",
                            max_chars=200,
                            height=80,
                            key=f"edit_notes_{song_id}",
                        )
                        edit_col, del_col = st.columns([3, 1])
                        with edit_col:
                            if st.form_submit_button(
                                "수정 저장", use_container_width=True
                            ):
                                if not new_title.strip():
                                    st.warning("제목을 입력해 주세요.")
                                else:
                                    with st.spinner("저장 중..."):
                                        ok = db.update_song(
                                            song_id, new_title, new_notes
                                        )
                                    if ok:
                                        st.toast(f"「{new_title}」 수정 완료!")
                                        after_write()
                        with del_col:
                            if st.form_submit_button(
                                "🗑️ 삭제", use_container_width=True
                            ):
                                with st.spinner("삭제 중..."):
                                    ok = db.delete_song(song_id)
                                if ok:
                                    st.toast(f"「{song['title']}」 삭제됨")
                                    st.session_state.vote_page = max(0, page - 1) if not page_songs[1:] else page
                                    after_write()

    # 페이지 네비게이션 (하단)
    st.divider()
    bot_left, bot_mid, bot_right = st.columns([1, 2, 1])
    with bot_left:
        if st.button("◀ 이전 ", disabled=(page == 0), use_container_width=True):
            st.session_state.vote_page -= 1
            st.rerun()
    with bot_mid:
        st.markdown(
            f"<p style='text-align:center;font-weight:600;'>"
            f"{page + 1} / {total_pages} 페이지"
            f"</p>",
            unsafe_allow_html=True,
        )
    with bot_right:
        if st.button("다음 ▶ ", disabled=(page >= total_pages - 1), use_container_width=True):
            st.session_state.vote_page += 1
            st.rerun()

def render_schedule_tab() -> None:
    if not is_authenticated():
        render_login_required()
        return

    user = authenticated_user()
    if is_guest():
        subtitle = (
            f"Guest는 팀 가능 인원 요약을 보기 전용으로 확인할 수 있습니다 "
            f"({TEAM_SIZE}명 기준)."
        )
    else:
        subtitle = (
            f"{user}님, 드래그로 가능한 시간을 선택한 뒤 표 하단 저장하기를 눌러주세요. "
            f"팀 요약은 아래에서 확인할 수 있습니다 ({TEAM_SIZE}명 기준)."
        )
    render_section_header("일정 조정", "일정 조정", subtitle)

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

    dates_payload = dates_for_component(start_date, end_date)
    times_payload = time_slots()

    if not dates_payload:
        st.warning("선택한 일정 범위에 날짜가 없습니다.")
        return

    if can_write():
        with st.spinner("내 일정 불러오는 중..."):
            member_slots = load_member_availability(user, start_date, end_date)
        if member_slots is None:
            return

        selected_payload = {k: bool(v) for k, v in member_slots.items() if v}

        st.markdown(f"**{user}님의 가능 시간** · 드래그로 선택")

        component_key = f"drag_{user}_{start_date}_{end_date}"
        component_result = drag_schedule_timetable(
            dates=dates_payload,
            times=times_payload,
            selected=selected_payload,
            key=component_key,
        )

        if component_result and component_result.get("action") == "save":
            new_slots = component_result.get("slots", {})
            save_fingerprint = schedule_save_fingerprint(
                user, start_date, end_date, new_slots
            )
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
    else:
        st.info("Guest는 개인 가능 시간을 입력하거나 저장할 수 없습니다.")

    st.divider()
    with st.spinner("팀 일정 불러오는 중..."):
        all_availability = load_all_availability(start_date, end_date)
    if all_availability is None:
        return

    st.markdown(
        f"**팀 가능 인원 요약** · 각 칸 = `가능 인원 / {TEAM_SIZE}` "
        "(진할수록 가능 인원 비율이 높음)"
    )

    st.caption("셀을 클릭하면 해당 시간대의 가능 인원을 바로 확인할 수 있습니다.")
    clicked = availability_summary_table(
        dates=dates_payload,
        times=times_payload,
        all_availability=all_availability,
        members=ACTUAL_MEMBERS,
        team_size=TEAM_SIZE,
        key=f"avail_table_{start_date}_{end_date}",
    )

    if clicked:
        st.session_state.selected_availability_slot = (
            clicked["label"], clicked["time"], clicked["date"]
        )

    if st.session_state.get("selected_availability_slot"):
        col_name, clicked_time, clicked_iso = st.session_state.selected_availability_slot
        clicked_key = slot_key(clicked_iso, clicked_time)

        available_members = [
            m for m in ACTUAL_MEMBERS
            if all_availability.get(m, {}).get(clicked_key, False)
        ]
        unavailable_members = [
            m for m in ACTUAL_MEMBERS
            if not all_availability.get(m, {}).get(clicked_key, False)
        ]

        st.markdown(f"##### 📋 {col_name} {clicked_time}")
        avail_col, unavail_col = st.columns(2)
        with avail_col:
            with st.container(border=True):
                st.markdown(f"**✅ 가능 — {len(available_members)}명**")
                if available_members:
                    for m in available_members:
                        st.markdown(f"- {m}")
                else:
                    st.caption("가능한 인원이 없습니다.")
        with unavail_col:
            with st.container(border=True):
                st.markdown(f"**⬜ 미입력/불가 — {len(unavailable_members)}명**")
                if unavailable_members:
                    for m in unavailable_members:
                        st.markdown(f"- {m}")
                else:
                    st.caption("모든 인원이 가능합니다.")

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
    render_section_header(
        "합주실 예약",
        "합주실 예약",
        "자주 쓰는 합주실 예약 페이지를 바로 열 수 있습니다.",
    )
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

        /* ── 메인 배경 ── */
        .stApp {
            background: linear-gradient(160deg, #f4f6fb 0%, #eef1f8 45%, #e8ecf4 100%);
        }

        /* ── 사이드바 ── */
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
            padding: 0.5rem 0.7rem 1.5rem;
        }
        [data-testid="stSidebar"] * { color: #ece9f5 !important; }
        [data-testid="stSidebar"] hr {
            margin: 1.25rem 0 1.5rem !important;
            border-color: rgba(255, 255, 255, 0.12) !important;
        }

        /* ── 사이드바 헤더 ── */
        .sidebar-header-wrap { padding: 0.25rem 0.35rem 0.5rem; }
        .sidebar-brand {
            font-size: clamp(2.35rem, 9vw, 3.4rem) !important;
            font-weight: 800 !important;
            letter-spacing: 0;
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
            letter-spacing: 0;
            font-weight: 700 !important;
            margin: 0 0 1rem 0.35rem !important;
        }

        /* ── 사이드바 메뉴 버튼 ── */
        [data-testid="stSidebar"] div:has(> .stButton) {
            width: 100% !important;
            max-width: none !important;
        }
        [data-testid="stSidebar"] .stButton {
            width: 100% !important;
            max-width: none !important;
            margin: 0 0 0.85rem 0 !important;
        }
        [data-testid="stSidebar"] .stButton > button {
            width: 100% !important;
            max-width: none !important;
            min-height: clamp(4.75rem, 8vw, 5.8rem);
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            text-align: left !important;
            padding: 1.3rem 1.55rem !important;
            border-radius: 16px !important;
            background: rgba(255, 255, 255, 0.065) !important;
            border: 1.5px solid rgba(255, 255, 255, 0.12);
            color: #f5f2ff !important;
            font-size: clamp(1.08rem, 4.2vw, 1.3rem) !important;
            font-weight: 750 !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.07) !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            transform: translateY(-1px) !important;
            background: rgba(167, 139, 250, 0.18) !important;
            border-color: rgba(196, 181, 253, 0.42) !important;
        }
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, rgba(244, 63, 94, 0.82), rgba(99, 102, 241, 0.72)) !important;
            border-color: rgba(196, 181, 253, 0.65) !important;
            box-shadow: 0 14px 34px rgba(76, 29, 149, 0.34) !important;
        }

        /* ── 사이드바 크레딧 ── */
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

        .role-badge {
            margin: 0.8rem 0 0;
            padding: 0.75rem 0.85rem;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.13);
            background: rgba(255, 255, 255, 0.07);
            display: flex;
            align-items: center;
            justify-content: flex-start;
            gap: 0.55rem;
        }
        .role-badge span {
            color: #14121f !important;
            border-radius: 999px;
            padding: 0.22rem 0.58rem;
            font-size: 0.76rem;
            font-weight: 800;
            background: #ddd6fe;
        }
        .role-badge strong {
            color: #f5f2ff !important;
            font-size: 0.95rem;
            font-weight: 750;
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .role-admin span { background: #fecdd3; }
        .role-member span { background: #bfdbfe; }
        .role-guest span { background: #bbf7d0; }

        /* ── 사이드바 입력창 가독성 ── */
        [data-testid="stSidebar"] .stTextInput input {
            color: #1e1a2e !important;
            background-color: rgba(255, 255, 255, 0.93) !important;
            border-radius: 10px !important;
            border: 1.5px solid rgba(167, 139, 250, 0.3) !important;
            font-weight: 500 !important;
        }
        [data-testid="stSidebar"] .stTextInput input::placeholder {
            color: #9990b0 !important;
        }
        [data-testid="stSidebar"] .stTextInput label,
        [data-testid="stSidebar"] .stSelectbox > label {
            font-size: 0.8rem !important;
            color: #a099bc !important;
            font-weight: 600 !important;
            letter-spacing: 0 !important;
            text-transform: uppercase;
        }
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
            background-color: rgba(255, 255, 255, 0.93) !important;
            border-radius: 10px !important;
            border: 1.5px solid rgba(167, 139, 250, 0.3) !important;
        }
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span,
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] div,
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] input,
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] p {
            color: #2d1f4e !important;
            font-weight: 500 !important;
        }
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] svg {
            fill: #2d1f4e !important;
        }
        [data-testid="stSidebar"] .stAlert {
            border-radius: 10px !important;
            padding: 0.5rem 0.75rem !important;
            font-size: 0.85rem !important;
        }

        /* ── 메인 제목 ── */
        h1 {
            font-weight: 800 !important;
            letter-spacing: 0;
            background: linear-gradient(120deg, #1e1b2e 0%, #5b21b6 50%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .login-shell {
            max-width: 920px;
            margin: clamp(3rem, 9vh, 7rem) auto 1.25rem;
        }
        .login-card {
            border-radius: 22px;
            padding: clamp(1.6rem, 4vw, 2.4rem);
            background:
                linear-gradient(135deg, rgba(124, 58, 237, 0.12), rgba(37, 99, 235, 0.08)),
                rgba(255, 255, 255, 0.78);
            border: 1px solid rgba(124, 58, 237, 0.16);
            box-shadow: 0 22px 60px rgba(30, 27, 46, 0.08);
        }
        .login-kicker {
            display: inline-flex;
            border-radius: 999px;
            padding: 0.34rem 0.68rem;
            background: rgba(124, 58, 237, 0.12);
            color: #6d28d9;
            font-size: 0.78rem;
            font-weight: 850;
            line-height: 1;
        }
        .login-card h1 {
            margin: 0.65rem 0 0 !important;
            font-size: clamp(2rem, 5vw, 3rem);
        }
        .login-card p {
            margin: 0.75rem 0 0 !important;
            color: #64748b;
            font-size: 1rem;
            line-height: 1.55;
        }
        .guest-panel {
            height: 100%;
            min-height: 9.2rem;
            border-radius: 20px;
            padding: 1.25rem;
            background:
                linear-gradient(135deg, rgba(5, 150, 105, 0.12), rgba(37, 99, 235, 0.08)),
                rgba(255, 255, 255, 0.75);
            border: 1px solid rgba(5, 150, 105, 0.16);
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
        }
        .guest-panel strong {
            color: #047857;
            font-size: 1.2rem;
            font-weight: 850;
        }
        .guest-panel p {
            margin: 0.55rem 0 0 !important;
            color: #475569;
            line-height: 1.55;
        }

        .schedule-banner {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            flex-wrap: wrap;
            padding: 1rem 1.15rem;
            margin: 0.25rem 0 1rem;
            border-radius: 16px;
            background:
                linear-gradient(135deg, rgba(16, 185, 129, 0.14), rgba(37, 99, 235, 0.08)),
                rgba(255, 255, 255, 0.78);
            border: 1px solid rgba(16, 185, 129, 0.18);
            box-shadow: 0 12px 34px rgba(15, 23, 42, 0.06);
        }
        .schedule-pin {
            width: 2.3rem;
            height: 2.3rem;
            border-radius: 12px;
            display: grid;
            place-items: center;
            background: rgba(255, 255, 255, 0.78);
            box-shadow: inset 0 0 0 1px rgba(16, 185, 129, 0.16);
        }
        .schedule-copy {
            display: flex;
            flex-direction: column;
            gap: 0.12rem;
        }
        .schedule-copy span {
            color: #047857;
            font-size: 0.78rem;
            font-weight: 800;
        }
        .schedule-copy strong {
            color: #102a43;
            font-size: 1.06rem;
            font-weight: 850;
        }
        .schedule-time,
        .schedule-note {
            border-radius: 999px;
            padding: 0.42rem 0.78rem;
            font-weight: 750;
            background: rgba(255, 255, 255, 0.7);
            color: #0f172a;
            border: 1px solid rgba(15, 23, 42, 0.07);
        }
        .schedule-note {
            color: #047857;
            background: rgba(16, 185, 129, 0.1);
        }
        .schedule-list-row {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            flex-wrap: wrap;
            padding: 0.35rem 0;
        }
        .schedule-list-row strong { color: #1e1b2e; }
        .schedule-list-row span { color: #475569; font-weight: 650; }
        .schedule-list-row em {
            color: #047857;
            font-style: normal;
            font-weight: 650;
        }

        .section-header {
            --section-accent: #6366f1;
            --section-accent-soft: rgba(99, 102, 241, 0.12);
            display: flex;
            align-items: flex-start;
            gap: 0.9rem;
            padding: 0.2rem 0 0.7rem;
            margin-top: 0.1rem;
        }
        .section-kicker {
            flex: 0 0 auto;
            border-radius: 999px;
            padding: 0.33rem 0.68rem;
            background: var(--section-accent-soft);
            color: var(--section-accent);
            font-size: 0.74rem;
            font-weight: 850;
            line-height: 1;
        }
        .section-header h2 {
            margin: 0 !important;
            color: #1f1738;
            font-size: clamp(1.35rem, 3.4vw, 1.85rem);
            font-weight: 850;
            line-height: 1.2;
        }
        .section-header p {
            margin: 0.25rem 0 0 !important;
            color: #64748b;
            font-size: 0.98rem;
            line-height: 1.5;
        }

        .dashboard-card {
            --dash-accent: #7c3aed;
            min-height: 8rem;
            border-radius: 18px;
            padding: 1rem;
            margin-bottom: 1rem;
            background:
                linear-gradient(135deg, color-mix(in srgb, var(--dash-accent) 10%, transparent), rgba(255, 255, 255, 0.72)),
                rgba(255, 255, 255, 0.78);
            border: 1px solid color-mix(in srgb, var(--dash-accent) 22%, rgba(148, 163, 184, 0.18));
            box-shadow: 0 14px 34px rgba(30, 27, 46, 0.06);
        }
        .dashboard-card span {
            display: inline-flex;
            border-radius: 999px;
            padding: 0.25rem 0.58rem;
            background: color-mix(in srgb, var(--dash-accent) 13%, white);
            color: var(--dash-accent);
            font-size: 0.76rem;
            font-weight: 850;
            line-height: 1;
        }
        .dashboard-card strong {
            display: block;
            margin-top: 0.75rem;
            color: #1e1b2e;
            font-size: clamp(1.25rem, 3vw, 1.65rem);
            line-height: 1.25;
            font-weight: 850;
        }
        .dashboard-card p {
            margin: 0.35rem 0 0 !important;
            color: #64748b;
            font-size: 0.92rem;
            line-height: 1.45;
        }
        div:has(> .dashboard-card) {
            margin-bottom: 0.35rem;
        }
        @media (max-width: 640px) {
            .dashboard-card {
                min-height: 7.2rem;
                padding: 1.05rem;
                margin-bottom: 1.25rem;
            }
            div:has(> .dashboard-card) {
                margin-bottom: 0.55rem;
            }
        }

        /* ── 메인 버튼 ── */
        .stButton > button {
            background: linear-gradient(135deg, #7c3aed 0%, #6366f1 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 2px 10px rgba(124, 58, 237, 0.25) !important;
        }
        .stButton > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(124, 58, 237, 0.4) !important;
        }
        .stButton > button:active {
            transform: translateY(0px) !important;
        }

        /* ── 곡 카드 ── */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 20px !important;
            border: 1.5px solid rgba(139, 92, 246, 0.15) !important;
            background: rgba(255, 255, 255, 0.82) !important;
            box-shadow: 0 2px 16px rgba(30, 27, 46, 0.06) !important;
            backdrop-filter: blur(8px) !important;
            transition: box-shadow 0.2s ease !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            box-shadow: 0 6px 28px rgba(124, 58, 237, 0.13) !important;
        }
        .song-head {
            padding: 0.1rem 0 0.25rem;
        }
        .song-tag {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.24rem 0.58rem;
            background: rgba(244, 63, 94, 0.11);
            color: #e11d48;
            font-size: 0.72rem;
            font-weight: 850;
            line-height: 1;
            margin-bottom: 0.5rem;
        }
        .song-head h3 {
            margin: 0 !important;
            color: #1e1b2e;
            font-size: clamp(1.18rem, 2.6vw, 1.55rem);
            line-height: 1.3;
            font-weight: 850;
        }
        .song-meta {
            margin: 0.25rem 0 0 !important;
            color: #7c3aed;
            font-size: 0.88rem;
            font-weight: 700;
        }
        .song-note {
            margin: 0.45rem 0 0 !important;
            display: inline-flex;
            max-width: 100%;
            border-radius: 10px;
            padding: 0.42rem 0.62rem;
            background: rgba(15, 23, 42, 0.04);
            color: #475569;
            font-size: 0.88rem;
            line-height: 1.45;
        }
        .comment-row {
            padding: 0.58rem 0.68rem;
            margin: 0.3rem 0;
            border-radius: 12px;
            background: rgba(248, 250, 252, 0.9);
            border: 1px solid rgba(148, 163, 184, 0.16);
        }
        .comment-row div {
            display: flex;
            align-items: baseline;
            gap: 0.45rem;
            flex-wrap: wrap;
        }
        .comment-row strong {
            color: #1e1b2e;
            font-size: 0.9rem;
        }
        .comment-row span {
            color: #94a3b8;
            font-size: 0.78rem;
            font-weight: 650;
        }
        .comment-row p {
            margin: 0.25rem 0 0 !important;
            color: #334155;
            font-size: 0.92rem;
            line-height: 1.55;
        }

        /* ── 메트릭 ── */
        [data-testid="stMetric"] {
            background: linear-gradient(135deg, #f5f3ff, #ede9fe) !important;
            border-radius: 14px !important;
            padding: 0.85rem 1rem !important;
            border: 1px solid rgba(139, 92, 246, 0.18) !important;
        }
        [data-testid="stMetricValue"] {
            color: #5b21b6 !important;
            font-weight: 700 !important;
        }
        [data-testid="stMetricDelta"] svg { display: none !important; }

        /* ── 익스팬더 ── */
        [data-testid="stExpander"] {
            border-radius: 16px !important;
            border: 1.5px solid rgba(139, 92, 246, 0.15) !important;
            background: rgba(255, 255, 255, 0.65) !important;
            overflow: hidden !important;
            box-shadow: 0 2px 10px rgba(30, 27, 46, 0.04) !important;
        }

        /* ── 메인 영역 입력창 ── */
        .stTextInput input,
        .stTextArea textarea {
            border-radius: 12px !important;
            border: 1.5px solid rgba(139, 92, 246, 0.2) !important;
            background: rgba(255, 255, 255, 0.9) !important;
            transition: border-color 0.2s, box-shadow 0.2s !important;
        }
        .stTextInput input:focus,
        .stTextArea textarea:focus {
            border-color: rgba(124, 58, 237, 0.5) !important;
            box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.08) !important;
        }

        /* ── 메인 영역 셀렉트박스 ── */
        .stSelectbox [data-baseweb="select"] > div {
            border-radius: 12px !important;
            border: 1.5px solid rgba(139, 92, 246, 0.2) !important;
            background: rgba(255, 255, 255, 0.9) !important;
        }

        /* ── 폼 ── */
        [data-testid="stForm"] {
            border-radius: 20px !important;
            border: 1.5px solid rgba(139, 92, 246, 0.13) !important;
            background: rgba(255, 255, 255, 0.55) !important;
            backdrop-filter: blur(6px) !important;
            padding: 1.25rem !important;
        }

        /* ── 슬라이더 ── */
        [data-testid="stSlider"] [role="slider"] {
            background: #7c3aed !important;
            border-color: #7c3aed !important;
        }

        /* ── 구분선 ── */
        hr { border-color: rgba(139, 92, 246, 0.1) !important; }

        /* ── 비디오 ── */
        [data-testid="stVideo"] { max-width: 320px; }
        [data-testid="stVideo"] iframe {
            border-radius: 14px;
            box-shadow: 0 6px 24px rgba(30, 27, 46, 0.12);
        }

        /* ── 링크 버튼 ── */
        .stLinkButton > a {
            background: linear-gradient(135deg, #059669, #0f766e) !important;
            color: #ffffff !important;
            border: none !important;
            padding: 1.1rem 1.25rem !important;
            font-size: 1.08rem !important;
            font-weight: 600 !important;
            border-radius: 14px !important;
            box-shadow: 0 10px 26px rgba(5, 150, 105, 0.18) !important;
        }
        .stLinkButton > a:hover {
            filter: brightness(1.04);
            transform: translateY(-1px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    init_session_state()
    inject_styles()

    if not is_authenticated():
        render_login_page()
        return

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
        selected_menu = render_sidebar_menu()
        st.markdown(
            """
            <div class="sidebar-credit-wrap">
                <p class="sidebar-credit">Made by <span class="credit-name">@kbj110</span></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not is_authenticated():
        st.rerun()

    st.title("LAB A팀 합주 관리")
    render_confirmed_schedules_banner()
    st.divider()

    if selected_menu == "홈":
        render_home_tab()
    elif selected_menu == "선곡 투표":
        render_vote_tab()
    elif selected_menu == "일정 조정":
        render_schedule_tab()
    else:
        render_booking_tab()


if __name__ == "__main__":
    main()
