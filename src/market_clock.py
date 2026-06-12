# -*- coding: utf-8 -*-
"""Deterministic cross-market timestamp and scheduled-session engine."""

from __future__ import annotations

import json
from datetime import datetime, time, timezone
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo


CALENDAR_BASIS = "WEEKDAY_SCHEDULE_ONLY"


def _between(value: time, start: time, end: time) -> bool:
    return start <= value < end


def _us_session(local_time: time) -> str:
    if _between(local_time, time(4, 0), time(9, 30)):
        return "PRE_MARKET"
    if _between(local_time, time(9, 30), time(16, 0)):
        return "REGULAR_TAPE"
    if _between(local_time, time(16, 0), time(20, 0)):
        return "POST_MARKET"
    return "CLOSED"


def _hk_session(local_time: time) -> str:
    if _between(local_time, time(9, 0), time(9, 30)):
        return "PRE_OPEN_AUCTION"
    if _between(local_time, time(9, 30), time(12, 0)):
        return "REGULAR_TAPE"
    if _between(local_time, time(12, 0), time(13, 0)):
        return "LUNCH_BREAK"
    if _between(local_time, time(13, 0), time(16, 0)):
        return "REGULAR_TAPE"
    if _between(local_time, time(16, 0), time(16, 10)):
        return "CLOSING_AUCTION"
    return "CLOSED"


def _cn_session(local_time: time) -> str:
    if _between(local_time, time(9, 15), time(9, 30)):
        return "PRE_OPEN_AUCTION"
    if _between(local_time, time(9, 30), time(11, 30)):
        return "REGULAR_TAPE"
    if _between(local_time, time(11, 30), time(13, 0)):
        return "LUNCH_BREAK"
    if _between(local_time, time(13, 0), time(14, 57)):
        return "REGULAR_TAPE"
    if _between(local_time, time(14, 57), time(15, 0)):
        return "CLOSING_AUCTION"
    return "CLOSED"


MARKET_DEFINITIONS: tuple[
    tuple[str, str, str, Callable[[time], str]],
    ...,
] = (
    (
        "US_EQUITIES",
        "America/New_York",
        "US_EQUITIES_EXTENDED_MODEL",
        _us_session,
    ),
    (
        "HK_EQUITIES",
        "Asia/Hong_Kong",
        "HKEX_SECURITIES_MODEL",
        _hk_session,
    ),
    (
        "CN_A_SHARES",
        "Asia/Shanghai",
        "SSE_MAIN_BOARD_MODEL",
        _cn_session,
    ),
)
MARKET_TIMEZONES = {
    market_id: timezone_name
    for market_id, timezone_name, _, _ in MARKET_DEFINITIONS
}
MARKET_MODELS = {
    market_id: schedule_model
    for market_id, _, schedule_model, _ in MARKET_DEFINITIONS
}
MARKET_SESSION_RESOLVERS = {
    market_id: session_resolver
    for market_id, _, _, session_resolver in MARKET_DEFINITIONS
}
SESSION_STATUSES = frozenset(
    {
        "PRE_MARKET",
        "PRE_OPEN_AUCTION",
        "REGULAR_TAPE",
        "LUNCH_BREAK",
        "CLOSING_AUCTION",
        "POST_MARKET",
        "CLOSED",
        "WEEKEND_CLOSED",
    }
)


def _format_offset(local_datetime: datetime) -> str:
    offset = local_datetime.strftime("%z")
    return f"{offset[:3]}:{offset[3:]}"


def _build_market_clock(
    utc_observed_at: datetime,
    timezone_name: str,
    schedule_model: str,
    session_resolver: Callable[[time], str],
) -> dict:
    local_datetime = utc_observed_at.astimezone(ZoneInfo(timezone_name))
    session_status = (
        "WEEKEND_CLOSED"
        if local_datetime.weekday() >= 5
        else session_resolver(local_datetime.time())
    )
    return {
        "timestamp": local_datetime.isoformat(timespec="microseconds"),
        "timezone_name": timezone_name,
        "timezone_abbreviation": local_datetime.tzname(),
        "utc_offset": _format_offset(local_datetime),
        "schedule_model": schedule_model,
        "session_status": session_status,
        "calendar_basis": CALENDAR_BASIS,
        "holiday_calendar_applied": False,
    }


def generate_institutional_timestamp_matrix(
    observed_at: datetime | None = None,
) -> dict:
    """Project one absolute observation instant into three market clocks."""
    instant = observed_at or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("observed_at must be a timezone-aware datetime.")

    utc_observed_at = instant.astimezone(timezone.utc)
    market_clocks = {
        market_id: _build_market_clock(
            utc_observed_at,
            timezone_name,
            schedule_model,
            session_resolver,
        )
        for (
            market_id,
            timezone_name,
            schedule_model,
            session_resolver,
        ) in MARKET_DEFINITIONS
    }
    return {
        "telemetry_matrix_utc": (
            utc_observed_at.isoformat(timespec="microseconds").replace("+00:00", "Z")
        ),
        "market_clocks": market_clocks,
    }


def validate_timestamp_matrix(matrix: Mapping[str, Any]) -> dict[str, Any]:
    """Validate that all market clocks represent one absolute instant."""
    if not isinstance(matrix, Mapping):
        raise TypeError("telemetry timestamp matrix must be an object.")
    if set(matrix) != {"telemetry_matrix_utc", "market_clocks"}:
        raise ValueError(
            "telemetry timestamp matrix must contain telemetry_matrix_utc "
            "and market_clocks."
        )

    utc_text = matrix["telemetry_matrix_utc"]
    if not isinstance(utc_text, str) or not utc_text.endswith("Z"):
        raise ValueError("telemetry_matrix_utc must be an ISO-8601 UTC timestamp.")
    try:
        utc_instant = datetime.fromisoformat(utc_text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("telemetry_matrix_utc must be a valid timestamp.") from error

    market_clocks = matrix["market_clocks"]
    if not isinstance(market_clocks, Mapping):
        raise TypeError("market_clocks must be an object.")
    if set(market_clocks) != set(MARKET_TIMEZONES):
        raise ValueError("market_clocks must contain US, HK, and CN market clocks.")

    validated_clocks: dict[str, dict[str, Any]] = {}
    for market_id, timezone_name in MARKET_TIMEZONES.items():
        clock = market_clocks[market_id]
        if not isinstance(clock, Mapping):
            raise TypeError(f"{market_id} market clock must be an object.")
        validated_clock = dict(clock)
        try:
            local_instant = datetime.fromisoformat(str(validated_clock["timestamp"]))
        except (KeyError, ValueError) as error:
            raise ValueError(f"{market_id} timestamp must be valid ISO-8601.") from error
        if local_instant.tzinfo is None or local_instant.utcoffset() is None:
            raise ValueError(f"{market_id} timestamp must include a UTC offset.")
        if local_instant.astimezone(timezone.utc) != utc_instant:
            raise ValueError(f"{market_id} timestamp does not match the UTC instant.")
        if validated_clock.get("timezone_name") != timezone_name:
            raise ValueError(f"{market_id} timezone_name must be {timezone_name}.")
        expected_local = utc_instant.astimezone(ZoneInfo(timezone_name))
        expected_timestamp = expected_local.isoformat(timespec="microseconds")
        if validated_clock["timestamp"] != expected_timestamp:
            raise ValueError(f"{market_id} timestamp is not the canonical projection.")
        if validated_clock.get("timezone_abbreviation") != expected_local.tzname():
            raise ValueError(f"{market_id} timezone abbreviation is inconsistent.")
        if validated_clock.get("utc_offset") != _format_offset(expected_local):
            raise ValueError(f"{market_id} UTC offset is inconsistent.")
        if validated_clock.get("schedule_model") != MARKET_MODELS[market_id]:
            raise ValueError(f"{market_id} schedule_model is inconsistent.")
        session_status = validated_clock.get("session_status")
        if session_status not in SESSION_STATUSES:
            raise ValueError(f"{market_id} has an invalid session_status.")
        expected_status = (
            "WEEKEND_CLOSED"
            if expected_local.weekday() >= 5
            else MARKET_SESSION_RESOLVERS[market_id](expected_local.time())
        )
        if session_status != expected_status:
            raise ValueError(f"{market_id} session_status is inconsistent.")
        if validated_clock.get("calendar_basis") != CALENDAR_BASIS:
            raise ValueError(f"{market_id} must disclose {CALENDAR_BASIS}.")
        if validated_clock.get("holiday_calendar_applied") is not False:
            raise ValueError(
                f"{market_id} holiday_calendar_applied must be false "
                "until an exchange calendar is integrated."
            )
        validated_clocks[market_id] = validated_clock

    return {
        "telemetry_matrix_utc": utc_text,
        "market_clocks": validated_clocks,
    }


def main() -> int:  # pragma: no cover
    print(
        json.dumps(
            generate_institutional_timestamp_matrix(),
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
