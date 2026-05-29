import os

import streamlit.components.v1 as components

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
_drag_schedule = components.declare_component("drag_schedule", path=_FRONTEND_DIR)


def drag_schedule_timetable(
    dates: list[dict],
    times: list[str],
    selected: dict[str, bool],
    height: int = 720,
    key: str | None = None,
) -> dict | None:
    """드래그 타임테이블. 저장하기 클릭 시 {action, slots} 반환."""
    return _drag_schedule(
        dates=dates,
        times=times,
        selected=selected,
        height=height,
        key=key,
        default=None,
    )
