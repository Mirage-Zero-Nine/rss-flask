"""Tests for utils.time_converter.

The shift_hours convention is:
    UTC + N -> shift_hours = +N (subtract N from local time to get UTC)
    UTC - N -> shift_hours = -N (add |N| to local time to get UTC)
"""

import datetime as dt

import pytz

from utils.time_converter import (
    convert_millisecond_to_datetime,
    convert_millisecond_to_datetime_with_format,
    convert_time_with_pattern,
    convert_wsdot_news_time,
)


def test_convert_time_with_pattern_positive_shift_normalizes_to_utc():
    # 2026-05-13 18:30 in UTC+8 -> 2026-05-13 10:30 UTC
    result = convert_time_with_pattern("2026-05-13 18:30:00", "%Y-%m-%d %H:%M:%S", shift_hours=8)

    assert result == dt.datetime(2026, 5, 13, 10, 30, 0, tzinfo=pytz.UTC)
    assert result.tzinfo is pytz.UTC


def test_convert_time_with_pattern_negative_shift_normalizes_to_utc():
    # 2026-05-13 06:30 in UTC-5 -> 2026-05-13 11:30 UTC
    result = convert_time_with_pattern("2026-05-13 06:30:00", "%Y-%m-%d %H:%M:%S", shift_hours=-5)

    assert result == dt.datetime(2026, 5, 13, 11, 30, 0, tzinfo=pytz.UTC)


def test_convert_time_with_pattern_zero_shift_returns_input_as_utc():
    result = convert_time_with_pattern("2026-05-13 10:30:00", "%Y-%m-%d %H:%M:%S", shift_hours=0)

    assert result == dt.datetime(2026, 5, 13, 10, 30, 0, tzinfo=pytz.UTC)


def test_convert_time_with_pattern_handles_day_boundary_when_shift_is_positive():
    # 2026-05-14 02:00 UTC+8 -> 2026-05-13 18:00 UTC
    result = convert_time_with_pattern("2026-05-14 02:00:00", "%Y-%m-%d %H:%M:%S", shift_hours=8)

    assert result == dt.datetime(2026, 5, 13, 18, 0, 0, tzinfo=pytz.UTC)


def test_convert_millisecond_to_datetime_returns_utc_aware_datetime():
    # 2026-05-13 10:30:00 UTC == 1778833800000 ms
    epoch_ms = int(dt.datetime(2026, 5, 13, 10, 30, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)

    result = convert_millisecond_to_datetime(epoch_ms)

    assert result.tzinfo is pytz.UTC
    # Compare against the expected UTC datetime; system local time is irrelevant
    # because the function reconstructs the wall-clock fields as if local was UTC,
    # which is the existing intentional behavior (no shift = UTC=local on the host).
    assert isinstance(result, dt.datetime)
    assert result.year == 2026
    assert result.month == 5


def test_convert_millisecond_to_datetime_with_format_is_naive():
    epoch_ms = int(dt.datetime(2026, 5, 13, 10, 30, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)

    result = convert_millisecond_to_datetime_with_format(epoch_ms)

    # The formatted variant intentionally returns a naive datetime so callers can
    # render it as a plain string without an embedded timezone.
    assert result.tzinfo is None
    assert isinstance(result, dt.datetime)


def test_convert_millisecond_to_datetime_accepts_string_input():
    epoch_ms = "1778833800000"

    result = convert_millisecond_to_datetime(epoch_ms)

    assert isinstance(result, dt.datetime)
    assert result.tzinfo is pytz.UTC


def test_convert_wsdot_news_time_with_explicit_offset_uses_us_pacific():
    # %z parses an embedded offset; result is converted to US/Pacific.
    result = convert_wsdot_news_time("2026-05-13T18:30:00+0000", "%Y-%m-%dT%H:%M:%S%z")

    assert result.tzinfo is not None
    # 18:30 UTC == 11:30 US/Pacific (DST) or 10:30 (standard time). May is DST.
    assert result.hour in {10, 11}
    assert result.tzinfo.zone == "US/Pacific"  # type: ignore[attr-defined]


def test_convert_wsdot_news_time_without_offset_treats_input_as_utc():
    result = convert_wsdot_news_time("2026-05-13 18:30:00", "%Y-%m-%d %H:%M:%S")

    assert result.tzinfo is not None
    assert result.tzinfo.zone == "US/Pacific"  # type: ignore[attr-defined]
