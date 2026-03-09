from __future__ import annotations

import datetime as dt

HOUSEKEEPING_HHMM = {"0240", "0250", "1440", "1450"}
JAPAN_NETCDF_BOUNDS = {
    "lat_min": 24.0,
    "lat_max": 50.0,
    "lon_min": 123.0,
    "lon_max": 150.0,
}


def normalize_band(value: str) -> str:
    text = str(value).replace("B", "").replace("C", "").strip()
    band = int(text)
    if band < 1 or band > 16:
        raise ValueError(f"Invalid band: {value}")
    return f"{band:02d}"


def normalize_hsd_resolution(value: str) -> str:
    text = str(value).strip()
    if text not in {"05", "10", "20"}:
        raise ValueError("hsd resolution must be one of 05/10/20")
    return text


def normalize_obs_no(value: str) -> str:
    number = int(str(value).strip())
    if number < 1 or number > 4:
        raise ValueError("observation number must be 01..04")
    return f"{number:02d}"


def default_full_disk_segments() -> tuple[str, ...]:
    return tuple(f"S{k:02d}10" for k in range(1, 11))


def parse_hours(expr: str) -> list[int]:
    result: set[int] = set()
    for chunk in [x.strip() for x in expr.split(",") if x.strip()]:
        if "-" in chunk:
            start, end = [int(x.strip()) for x in chunk.split("-", 1)]
            if start > end:
                raise ValueError(f"Invalid hour range: {chunk}")
            values = range(start, end + 1)
        else:
            values = [int(chunk)]
        for hour in values:
            if hour < 0 or hour > 23:
                raise ValueError(f"Invalid hour: {hour}")
            result.add(hour)
    if not result:
        raise ValueError("utc_hours is empty")
    return sorted(result)


def to_datetime(value: str | dt.datetime) -> dt.datetime:
    if isinstance(value, dt.datetime):
        return value
    return dt.datetime.fromisoformat(str(value).strip().replace("T", " "))


def to_date(value: str | dt.date) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.datetime.strptime(str(value).strip(), "%Y-%m-%d").date()


def expected_minute_step(data_format: str, sector: str) -> float:
    if data_format == "netcdf":
        return 10.0
    if sector == "FLDK":
        return 10.0
    return 2.5


def acquisition_timedelta(sector: str) -> dt.timedelta:
    if sector in {"Target", "Japan"}:
        return dt.timedelta(minutes=2, seconds=30)
    if sector == "Landmark":
        return dt.timedelta(seconds=30)
    if sector == "FLDK":
        return dt.timedelta(minutes=10)
    raise ValueError(f"Unsupported sector: {sector}")
