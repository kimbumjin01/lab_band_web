import json
import os

import streamlit.components.v1 as components

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
_TEMPLATE_PATH = os.path.join(_FRONTEND_DIR, "index.template.html")
_INDEX_PATH = os.path.join(_FRONTEND_DIR, "index.html")

_drag_schedule = components.declare_component(
    "lab_band_drag_schedule",
    path=_FRONTEND_DIR,
)


def _write_index_html(dates: list[dict], times: list[str], selected: dict) -> None:
    with open(_TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    bootstrap = json.dumps(
        {"dates": dates, "times": times, "selected": selected},
        ensure_ascii=False,
    )
    html = template.replace(
        "/*__BOOTSTRAP__*/",
        f"const __BOOTSTRAP__ = {bootstrap};",
    )

    with open(_INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)


def drag_schedule_timetable(
    dates: list[dict],
    times: list[str],
    selected: dict[str, bool],
    height: int = 720,
    key: str | None = None,
) -> dict | None:
    """드래그 타임테이블. 저장하기 클릭 시 {action, slots} 반환."""
    if not dates or not times:
        return None

    _write_index_html(dates, times, selected)

    frame_height = min(900, max(480, 160 + len(times) * 36))
    return _drag_schedule(
        default=None,
        height=frame_height,
        key=key,
    )
