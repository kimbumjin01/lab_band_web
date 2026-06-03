import json
import os

import streamlit.components.v1 as components

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
_TEMPLATE_PATH = os.path.join(_FRONTEND_DIR, "index.template.html")
_INDEX_PATH = os.path.join(_FRONTEND_DIR, "index.html")

_availability_table = components.declare_component(
    "lab_band_availability_table",
    path=_FRONTEND_DIR,
)


def _write_index_html(dates, times, all_availability, members, team_size):
    with open(_TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()
    bootstrap = json.dumps(
        {
            "dates": dates,
            "times": times,
            "all_availability": all_availability,
            "members": members,
            "team_size": team_size,
        },
        ensure_ascii=False,
    )
    html = template.replace("/*__BOOTSTRAP__*/", f"const __BOOTSTRAP__ = {bootstrap};")
    with open(_INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)


def availability_summary_table(
    dates: list[dict],
    times: list[str],
    all_availability: dict,
    members: list[str],
    team_size: int,
    key: str | None = None,
) -> dict | None:
    if not dates or not times:
        return None
    _write_index_html(dates, times, all_availability, members, team_size)
    frame_height = max(200, 55 + len(times) * 36)
    return _availability_table(
        default=None,
        height=frame_height,
        key=key,
    )