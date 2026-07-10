import unittest
from datetime import date, time

from schedule_logic import (
    availability_rows_for_save,
    normalize_slot_time,
    schedule_save_fingerprint,
    slot_key,
)


class ScheduleLogicTest(unittest.TestCase):
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
