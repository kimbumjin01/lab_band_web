import logging
from datetime import date
from typing import Any

import streamlit as st
from supabase import Client, create_client

DB_ERROR_MESSAGE = "DB 연결 오류"
logger = logging.getLogger(__name__)


@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def _run_db(operation: str, fn: Any) -> Any:
    try:
        return fn()
    except Exception:
        logger.exception("DB error during %s", operation)
        st.error(DB_ERROR_MESSAGE)
        return None


def get_all_songs() -> list[dict] | None:
    def _fetch() -> list[dict]:
        response = (
            get_client()
            .table("songs")
            .select("id, title, youtube_url, uploaded_by, notes, created_at")
            .order("created_at", desc=True)
            .execute()
        )
        songs = response.data or []
        for song in songs:
            song["url"] = song["youtube_url"]
        return songs

    result = _run_db("get_all_songs", _fetch)
    return result if result is not None else None


def add_song(
    title: str, youtube_url: str, uploaded_by: str, notes: str = ""
) -> bool:
    def _insert() -> bool:
        get_client().table("songs").insert(
            {
                "title": title,
                "youtube_url": youtube_url,
                "uploaded_by": uploaded_by,
                "notes": notes.strip() or None,
            }
        ).execute()
        return True

    return _run_db("add_song", _insert) is True


def delete_song(song_id: int) -> bool:
    def _delete() -> bool:
        get_client().table("songs").delete().eq("id", song_id).execute()
        return True

    return _run_db("delete_song", _delete) is True


def get_votes(song_id: int) -> dict[str, int] | None:
    def _fetch() -> dict[str, int]:
        response = (
            get_client()
            .table("votes")
            .select("member, score")
            .eq("song_id", song_id)
            .execute()
        )
        return {row["member"]: int(row["score"]) for row in (response.data or [])}

    result = _run_db("get_votes", _fetch)
    return result if result is not None else None


def upsert_vote(song_id: int, member: str, score: int) -> bool:
    def _upsert() -> bool:
        get_client().table("votes").upsert(
            {
                "song_id": song_id,
                "member": member,
                "score": score,
            }
        ).execute()
        return True

    return _run_db("upsert_vote", _upsert) is True


def _to_slot_key(slot_date: str, slot_time: str) -> str:
    return f"{slot_date}|{slot_time}"


def get_member_availability(
    member: str, start_date: date, end_date: date
) -> dict[str, bool] | None:
    def _fetch() -> dict[str, bool]:
        response = (
            get_client()
            .table("availability")
            .select("slot_date, slot_time, available")
            .eq("member", member)
            .gte("slot_date", start_date.isoformat())
            .lte("slot_date", end_date.isoformat())
            .execute()
        )
        return {
            _to_slot_key(str(row["slot_date"]), row["slot_time"]): bool(row["available"])
            for row in (response.data or [])
        }

    result = _run_db("get_member_availability", _fetch)
    return result if result is not None else None


def get_all_availability(
    start_date: date, end_date: date
) -> dict[str, dict[str, bool]] | None:
    def _fetch() -> dict[str, dict[str, bool]]:
        response = (
            get_client()
            .table("availability")
            .select("member, slot_date, slot_time, available")
            .gte("slot_date", start_date.isoformat())
            .lte("slot_date", end_date.isoformat())
            .execute()
        )
        result: dict[str, dict[str, bool]] = {}
        for row in response.data or []:
            member = row["member"]
            key = _to_slot_key(str(row["slot_date"]), row["slot_time"])
            result.setdefault(member, {})[key] = bool(row["available"])
        return result

    result = _run_db("get_all_availability", _fetch)
    return result if result is not None else None


def upsert_availability(
    member: str, slot_date: date, slot_time: str, available: bool
) -> bool:
    return upsert_availability_batch(
        [
            {
                "member": member,
                "slot_date": slot_date.isoformat(),
                "slot_time": slot_time,
                "available": available,
            }
        ]
    )


def upsert_availability_batch(rows: list[dict]) -> bool:
    if not rows:
        return True

    def _upsert() -> bool:
        get_client().table("availability").upsert(rows).execute()
        return True

    return _run_db("upsert_availability_batch", _upsert) is True


@st.cache_data(ttl=30)
def get_confirmed_schedules() -> list[dict] | None:
    def _fetch() -> list[dict]:
        response = (
            get_client()
            .table("confirmed_schedules")
            .select("id, schedule_date, start_time, end_time, note, created_at")
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []

    result = _run_db("get_confirmed_schedules", _fetch)
    return result if result is not None else None


def add_confirmed_schedule(
    schedule_date: str, start_time: str, end_time: str, note: str
) -> bool:
    def _insert() -> bool:
        get_client().table("confirmed_schedules").insert(
            {
                "schedule_date": schedule_date,
                "start_time": start_time,
                "end_time": end_time,
                "note": note.strip() or None,
            }
        ).execute()
        return True

    return _run_db("add_confirmed_schedule", _insert) is True


def delete_confirmed_schedule(schedule_id: int) -> bool:
    def _delete() -> bool:
        get_client().table("confirmed_schedules").delete().eq("id", schedule_id).execute()
        return True

    return _run_db("delete_confirmed_schedule", _delete) is True
