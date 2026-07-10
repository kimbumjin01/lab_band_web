import json
import re
from datetime import date, datetime
from typing import Any, Mapping


_SLOT_TIME_PATTERN = re.compile(r"^(\d{1,2}):(\d{2})")


def normalize_member(value: Any) -> str:
    return str(value or "").strip()


def normalize_slot_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "").strip()


def normalize_slot_time(value: Any) -> str:
    """DB/UI 시간 표현을 팀 요약에서 사용하는 HH:MM 형태로 맞춘다."""
    if hasattr(value, "isoformat") and not isinstance(value, str):
        value = value.isoformat()

    text = str(value or "").strip()
    match = _SLOT_TIME_PATTERN.match(text)
    if not match:
        return text

    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23 or minute > 59:
        return text
    return f"{hour:02d}:{minute:02d}"


def slot_key(slot_date: Any, slot_time: Any) -> str:
    return f"{normalize_slot_date(slot_date)}|{normalize_slot_time(slot_time)}"


def normalize_slots(slots: Mapping[str, Any] | None) -> dict[str, bool]:
    normalized: dict[str, bool] = {}
    for raw_key, available in (slots or {}).items():
        if not isinstance(raw_key, str) or "|" not in raw_key:
            continue
        raw_date, raw_time = raw_key.split("|", 1)
        normalized_date = normalize_slot_date(raw_date)
        normalized_time = normalize_slot_time(raw_time)
        if not normalized_date or not normalized_time:
            continue
        key = f"{normalized_date}|{normalized_time}"
        normalized[key] = bool(available)
    return normalized


def availability_rows_for_save(
    member: str,
    new_slots: Mapping[str, Any] | None,
    old_slots: Mapping[str, Any] | None,
) -> list[dict]:
    """변경된 슬롯을 저장 행으로 만든다. 새 목록에서 빠진 기존 true는 false로 저장한다."""
    normalized_member = normalize_member(member)
    normalized_new = normalize_slots(new_slots)
    normalized_old = normalize_slots(old_slots)
    rows: list[dict] = []

    for key in sorted(set(normalized_new) | set(normalized_old)):
        new_value = bool(normalized_new.get(key, False))
        old_value = bool(normalized_old.get(key, False))
        if new_value == old_value:
            continue

        slot_date, slot_time = key.split("|", 1)
        rows.append(
            {
                "member": normalized_member,
                "slot_date": slot_date,
                "slot_time": slot_time,
                "available": new_value,
            }
        )

    return rows


def schedule_save_fingerprint(
    member: str,
    start_date: Any,
    end_date: Any,
    slots: Mapping[str, Any] | None,
) -> str:
    """다른 사용자/날짜 범위의 저장을 같은 요청으로 오인하지 않도록 범위를 포함한다."""
    payload = {
        "member": normalize_member(member),
        "start_date": normalize_slot_date(start_date),
        "end_date": normalize_slot_date(end_date),
        "slots": normalize_slots(slots),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
