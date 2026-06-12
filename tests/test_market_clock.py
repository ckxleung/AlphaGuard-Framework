from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class InstitutionalMarketClockTests(unittest.TestCase):
    def test_summer_matrix_applies_new_york_daylight_saving_time(self) -> None:
        from src.market_clock import generate_institutional_timestamp_matrix

        matrix = generate_institutional_timestamp_matrix(
            datetime(2026, 6, 12, 15, 8, 22, 104291, tzinfo=timezone.utc)
        )

        self.assertEqual(
            matrix["telemetry_matrix_utc"],
            "2026-06-12T15:08:22.104291Z",
        )
        us_clock = matrix["market_clocks"]["US_EQUITIES"]
        self.assertEqual(us_clock["timestamp"], "2026-06-12T11:08:22.104291-04:00")
        self.assertEqual(us_clock["timezone_abbreviation"], "EDT")
        self.assertEqual(us_clock["utc_offset"], "-04:00")
        self.assertEqual(us_clock["session_status"], "REGULAR_TAPE")

        self.assertEqual(
            matrix["market_clocks"]["HK_EQUITIES"]["session_status"],
            "CLOSED",
        )
        self.assertEqual(
            matrix["market_clocks"]["CN_A_SHARES"]["session_status"],
            "CLOSED",
        )

    def test_winter_matrix_applies_new_york_standard_time(self) -> None:
        from src.market_clock import generate_institutional_timestamp_matrix

        matrix = generate_institutional_timestamp_matrix(
            datetime(2026, 1, 15, 15, 0, tzinfo=timezone.utc)
        )

        us_clock = matrix["market_clocks"]["US_EQUITIES"]
        self.assertEqual(us_clock["timestamp"], "2026-01-15T10:00:00.000000-05:00")
        self.assertEqual(us_clock["timezone_abbreviation"], "EST")
        self.assertEqual(us_clock["session_status"], "REGULAR_TAPE")

    def test_us_extended_hours_are_not_mislabeled_as_regular_tape(self) -> None:
        from src.market_clock import generate_institutional_timestamp_matrix

        pre_market = generate_institutional_timestamp_matrix(
            datetime(2026, 6, 12, 12, 0, tzinfo=timezone.utc)
        )
        post_market = generate_institutional_timestamp_matrix(
            datetime(2026, 6, 12, 21, 0, tzinfo=timezone.utc)
        )

        self.assertEqual(
            pre_market["market_clocks"]["US_EQUITIES"]["session_status"],
            "PRE_MARKET",
        )
        self.assertEqual(
            post_market["market_clocks"]["US_EQUITIES"]["session_status"],
            "POST_MARKET",
        )

    def test_hk_and_cn_midday_breaks_are_explicit(self) -> None:
        from src.market_clock import generate_institutional_timestamp_matrix

        matrix = generate_institutional_timestamp_matrix(
            datetime(2026, 6, 12, 4, 30, tzinfo=timezone.utc)
        )

        self.assertEqual(
            matrix["market_clocks"]["HK_EQUITIES"]["session_status"],
            "LUNCH_BREAK",
        )
        self.assertEqual(
            matrix["market_clocks"]["CN_A_SHARES"]["session_status"],
            "LUNCH_BREAK",
        )

    def test_weekend_is_closed_and_calendar_limit_is_disclosed(self) -> None:
        from src.market_clock import generate_institutional_timestamp_matrix

        matrix = generate_institutional_timestamp_matrix(
            datetime(2026, 6, 13, 15, 0, tzinfo=timezone.utc)
        )

        for market_clock in matrix["market_clocks"].values():
            self.assertEqual(market_clock["session_status"], "WEEKEND_CLOSED")
            self.assertEqual(
                market_clock["calendar_basis"],
                "WEEKDAY_SCHEDULE_ONLY",
            )
            self.assertFalse(market_clock["holiday_calendar_applied"])

    def test_naive_datetime_is_rejected(self) -> None:
        from src.market_clock import generate_institutional_timestamp_matrix

        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            generate_institutional_timestamp_matrix(datetime(2026, 6, 12, 15, 0))

    def test_matrix_validator_rejects_desynchronized_market_clock(self) -> None:
        from src.market_clock import (
            generate_institutional_timestamp_matrix,
            validate_timestamp_matrix,
        )

        matrix = generate_institutional_timestamp_matrix(
            datetime(2026, 6, 12, 15, 0, tzinfo=timezone.utc)
        )
        matrix["market_clocks"]["HK_EQUITIES"]["timestamp"] = (
            "2026-06-12T23:00:01.000000+08:00"
        )

        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_timestamp_matrix(matrix)

    def test_pipeline_uses_injected_observation_time(self) -> None:
        from src.main_pipeline import run_daily_smoke

        report = run_daily_smoke(
            "NVDA",
            observed_at=datetime(
                2026,
                6,
                12,
                15,
                8,
                22,
                104291,
                tzinfo=timezone.utc,
            ),
        )

        self.assertNotIn("telemetry_timestamp", report)
        self.assertEqual(
            report["telemetry_timestamp_matrix"]["market_clocks"]
            ["US_EQUITIES"]["timezone_abbreviation"],
            "EDT",
        )


if __name__ == "__main__":
    unittest.main()
