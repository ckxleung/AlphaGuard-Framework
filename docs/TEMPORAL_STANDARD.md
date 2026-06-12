# AlphaGuard Cross-Market Temporal Standard

## Objective

Every AlphaGuard audit run must identify one absolute observation instant and
project that same instant into the United States, Hong Kong, and mainland China
market timezones. A local timestamp without its UTC offset is not acceptable.

The canonical implementation is `src/market_clock.py`.

## Required Matrix

```json
{
  "telemetry_matrix_utc": "2026-06-12T15:08:22.104291Z",
  "market_clocks": {
    "US_EQUITIES": {
      "timestamp": "2026-06-12T11:08:22.104291-04:00",
      "timezone_name": "America/New_York",
      "timezone_abbreviation": "EDT",
      "utc_offset": "-04:00",
      "schedule_model": "US_EQUITIES_EXTENDED_MODEL",
      "session_status": "REGULAR_TAPE",
      "calendar_basis": "WEEKDAY_SCHEDULE_ONLY",
      "holiday_calendar_applied": false
    }
  }
}
```

All three market clocks must resolve to the exact UTC instant in
`telemetry_matrix_utc`.

## Timezone Rules

- United States equities use `America/New_York`; `zoneinfo` determines EST or
  EDT for the observation date.
- Hong Kong equities use `Asia/Hong_Kong`.
- China A-shares use `Asia/Shanghai`.
- UTC is serialized with `Z`; local timestamps include numeric UTC offsets.
- Microseconds are retained to make ingestion ordering deterministic.

No third-party `pytz` dependency is required.

## Scheduled Session States

### United States Equities

- model: `US_EQUITIES_EXTENDED_MODEL`;
- `PRE_MARKET`: 04:00 to 09:30 local time;
- `REGULAR_TAPE`: 09:30 to 16:00;
- `POST_MARKET`: 16:00 to 20:00;
- `CLOSED`: all other weekday times.

The 04:00 to 20:00 extended-hours envelope is venue dependent. The model is
aligned to an extended-hours venue pattern such as NYSE Arca; it must not be
described as the universal session schedule for every US-listed instrument.

### Hong Kong Equities

- model: `HKEX_SECURITIES_MODEL`;
- `PRE_OPEN_AUCTION`: 09:00 to 09:30;
- `REGULAR_TAPE`: 09:30 to 12:00 and 13:00 to 16:00;
- `LUNCH_BREAK`: 12:00 to 13:00;
- `CLOSING_AUCTION`: 16:00 to 16:10;
- `CLOSED`: all other weekday times.

### China A-Shares

- model: `SSE_MAIN_BOARD_MODEL`;
- `PRE_OPEN_AUCTION`: 09:15 to 09:30;
- `REGULAR_TAPE`: 09:30 to 11:30 and 13:00 to 14:57;
- `LUNCH_BREAK`: 11:30 to 13:00;
- `CLOSING_AUCTION`: 14:57 to 15:00;
- `CLOSED`: all other weekday times.

Saturday and Sunday are reported as `WEEKEND_CLOSED`.

## Calendar Limitation

The current engine applies deterministic weekday schedules. It does not yet
apply exchange holiday calendars, half-day schedules, weather closures,
regulatory halts, or instrument-specific trading suspensions.

Every market clock therefore carries:

```json
{
  "calendar_basis": "WEEKDAY_SCHEDULE_ONLY",
  "holiday_calendar_applied": false
}
```

Downstream systems must not interpret `REGULAR_TAPE` as proof that an exchange
was actually open on a holiday or extraordinary closure date. A future
exchange-calendar adapter may set `holiday_calendar_applied` to true only after
the calendar source, version, and effective date are captured.

## Primary Schedule References

- NYSE, Holidays and Trading Hours:
  https://www.nyse.com/markets/hours-calendars
- HKEX, Securities Market Trading Hours:
  https://www.hkex.com.hk/Services/Trading/Securities/Overview/Trading-Hours
- Shanghai Stock Exchange, Trading Schedule:
  https://english.sse.com.cn/start/trading/schedule/

## Deterministic Testing

Tests must inject a timezone-aware `datetime`. Tests may not depend on the
machine's local timezone or current wall clock.

Required boundary coverage includes:

- New York EDT and EST dates;
- pre-market, regular, and post-market transitions;
- Hong Kong and China midday breaks;
- weekends;
- rejection of naive datetimes;
- rejection of market clocks that do not reconcile to the UTC instant.
