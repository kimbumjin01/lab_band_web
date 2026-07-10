import unittest
from datetime import date, datetime, time, timedelta, timezone

from schedule_logic import (
    availability_rows_for_save,
    fetch_all_pages,
    normalize_slot_time,
    schedule_save_fingerprint,
    slot_key,
    upcoming_schedules,
)


class ScheduleLogicTest(unittest.TestCase):
    def test_upcoming_schedules_use_current_time_and_start_order(self) -> None:
        schedules = [
            {
                "id": 3,
                "schedule_date": "2026-08-04",
                "start_time": "19:00:00",
                "end_time": "21:00:00",
            },
            {
                "id": 1,
                "schedule_date": "2026-07-09",
                "start_time": "19:00:00",
                "end_time": "21:00:00",
            },
            {
                "id": 2,
                "schedule_date": "2026-07-16",
                "start_time": "18:00:00",
                "end_time": "20:00:00",
            },
        ]
        kst = timezone(timedelta(hours=9))
        now = datetime(2026, 7, 10, 12, 0, tzinfo=kst)

        result = upcoming_schedules(schedules, now)

        self.assertEqual([schedule["id"] for schedule in result], [2, 3])

    def test_upcoming_schedules_include_an_ongoing_practice(self) -> None:
        schedule = {
            "id": 1,
            "schedule_date": "2026-07-10",
            "start_time": "19:00",
            "end_time": "21:00",
        }
        now = datetime(2026, 7, 10, 20, 0)

        self.assertEqual(upcoming_schedules([schedule], now), [schedule])

    def test_fetches_all_pages_even_when_server_cap_is_smaller(self) -> None:
        source = [{"id": index} for index in range(1205)]
        requested_ranges: list[tuple[int, int]] = []

        def fetch_page(start: int, end: int) -> list[dict]:
            requested_ranges.append((start, end))
            server_cap = 400
            return source[start : min(end + 1, start + server_cap)]

        rows = fetch_all_pages(fetch_page, page_size=1000)

        self.assertEqual(rows, source)
        self.assertEqual(
            requested_ranges,
            [(0, 999), (400, 1399), (800, 1799), (1200, 2199), (1205, 2204)],
        )

    def test_normalizes_database_time_to_ui_key(self) -> None:
        self.assertEqual(normalize_slot_time("13:00:00"), "13:00")
        self.assertEqual(normalize_slot_time(time(9, 30)), "09:30")
        self.assertEqual(slot_key(date(2026, 8, 2), "13:00:00"), "2026-08-02|13:00")

    def test_builds_rows_for_new_and_removed_slots(self) -> None:
        rows = availability_rows_for_save(
            " 이해진 ",
            {"2026-08-02|14:00": True},
            {
                "2026-08-02|13:00:00": True,
                "2026-08-02|14:00:00": False,
            },
        )

        self.assertEqual(
            rows,
            [
                {
                    "member": "이해진",
                    "slot_date": "2026-08-02",
                    "slot_time": "13:00",
                    "available": False,
                },
                {
                    "member": "이해진",
                    "slot_date": "2026-08-02",
                    "slot_time": "14:00",
                    "available": True,
                },
            ],
        )

    def test_equivalent_time_formats_are_not_written_again(self) -> None:
        rows = availability_rows_for_save(
            "이해진",
            {"2026-08-02|13:00": True},
            {"2026-08-02|13:00:00": True},
        )
        self.assertEqual(rows, [])

    def test_save_fingerprint_is_scoped_to_member_and_date_range(self) -> None:
        slots = {"2026-08-02|13:00": True}
        base = schedule_save_fingerprint(
            "김범진", date(2026, 8, 2), date(2026, 8, 5), slots
        )
        other_member = schedule_save_fingerprint(
            "이해진", date(2026, 8, 2), date(2026, 8, 5), slots
        )
        other_range = schedule_save_fingerprint(
            "김범진", date(2026, 8, 3), date(2026, 8, 5), slots
        )

        self.assertNotEqual(base, other_member)
        self.assertNotEqual(base, other_range)


if __name__ == "__main__":
    unittest.main()
