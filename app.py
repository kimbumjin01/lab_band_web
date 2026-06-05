import json
from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import streamlit as st

import db
from availability_table import availability_summary_table
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

MENU_OPTIONS = ["선곡 투표", "일정 조정", "합주실 예약"]
MENU_ICONS = {
    "선곡 투표": "🎵",
    "일정 조정": "📅",
    "합주실 예약": "🎹",
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


def slot_key(iso_date: str, time_slot: str) -> str:
    return f"{iso_date}|{time_slot}"


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
    prev_user = st.session_state.get("last_selected_user", NAME_PLACEHOLDER)
    selected = st.selectbox("이름 선택", MEMBER_OPTIONS, key="global_user")

    if selected != prev_user:
        st.session_state.authenticated_member = None
        st.session_state.pw_input = ""
        st.session_state.last_selected_user = selected

    if selected == GUEST_USER:
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
                st.session_state.authenticated_member = selected
            else:
                st.session_state.authenticated_member = None
                st.warning("비밀번호가 올바르지 않습니다.")

    if is_authenticated():
        auth_label = (
            "Guest 보기 전용 접속 중"
            if is_guest()
            else f"{authenticated_user()}님 로그인됨"
        )
        st.markdown(
            f"<p style='color:#a78bfa;font-weight:700;font-size:0.9rem;"
            f"margin:0.5rem 0 0 0.2rem;'>✓ {auth_label}</p>",
            unsafe_allow_html=True,
        )


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
    if is_guest():
        st.caption("Guest는 등록된 곡과 의견을 보기 전용으로 확인할 수 있습니다.")
    else:
        st.caption(f"{user}님, 곡을 추가하고 1~5점으로 투표해 보세요.")

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

    # ── 페이지네이션 ──
    total = len(songs)
    total_pages = max(1, (total + SONGS_PER_PAGE - 1) // SONGS_PER_PAGE)
    page = min(st.session_state.vote_page, total_pages - 1)
    st.session_state.vote_page = page
    page_songs = songs[page * SONGS_PER_PAGE : (page + 1) * SONGS_PER_PAGE]

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
            f"{page + 1} / {total_pages} 페이지 &nbsp;·&nbsp; 전체 {total}곡"
            f"</p>",
            unsafe_allow_html=True,
        )
    with nav_right:
        if st.button("다음 ▶", disabled=(page >= total_pages - 1), use_container_width=True):
            st.session_state.vote_page += 1
            st.rerun()

    st.divider()

    for song in page_songs:
        song_id = int(song["id"])
        votes = all_votes.get(song_id, {})
        comments = all_comments.get(song_id, [])

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
                        st.markdown(
                            f"**{display_name}** "
                            f"<span style='color:#9ca3af;font-size:0.8rem'>"
                            f"{c['created_at'][:10]}</span>  \n{c['content']}",
                            unsafe_allow_html=True,
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
    st.subheader("일정 조정")
    if is_guest():
        st.caption(
            f"Guest는 팀 가능 인원 요약을 보기 전용으로 확인할 수 있습니다 "
            f"({TEAM_SIZE}명 기준)."
        )
    else:
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
            padding: 0.5rem 0.25rem 1.5rem;
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

        /* ── 사이드바 메뉴 라디오 ── */
        [data-testid="stSidebar"] .stRadio {
            flex: 1;
            width: calc(100% + 0.8rem);
            margin-left: -0.4rem;
            margin-right: -0.4rem;
            padding: 0 !important;
        }
        [data-testid="stSidebar"] .stRadio > label { display: none; }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
            gap: clamp(0.65rem, 2.5vw, 1rem) !important;
            width: 100% !important;
            max-width: none !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: stretch !important;
            padding: 0 !important;
        }
        [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] {
            background: rgba(255, 255, 255, 0.06);
            border: 1.5px solid rgba(255, 255, 255, 0.12);
            border-radius: 18px;
            padding: clamp(1.15rem, 4.5vw, 1.6rem) clamp(1.3rem, 5vw, 1.75rem) !important;
            display: flex !important;
            align-items: center !important;
            width: 100% !important;
            max-width: none !important;
            box-sizing: border-box !important;
            min-height: 3.5rem;
            font-size: clamp(1.35rem, 5.5vw, 1.65rem) !important;
            font-weight: 650 !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"]:hover {
            background: rgba(167, 139, 250, 0.15) !important;
            border-color: rgba(167, 139, 250, 0.35) !important;
        }
        [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"]:has(input:checked) {
            background: linear-gradient(135deg, rgba(124,58,237,0.55), rgba(99,102,241,0.4)) !important;
            border-color: rgba(196, 181, 253, 0.65) !important;
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
            letter-spacing: 0.06em !important;
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
            letter-spacing: -0.03em;
            background: linear-gradient(120deg, #1e1b2e 0%, #5b21b6 50%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
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
