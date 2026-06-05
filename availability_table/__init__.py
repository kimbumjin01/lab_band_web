import os

import streamlit.components.v1 as components

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

_availability_table = components.declare_component(
    "lab_band_availability_table",
    path=_FRONTEND_DIR,
)


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
    frame_height = max(200, 55 + len(times) * 36)
    return _availability_table(
        dates=dates,
        times=times,
        all_availability=all_availability,
        members=members,
        team_size=team_size,
        default=None,
        height=frame_height,
        key=key,
    )
