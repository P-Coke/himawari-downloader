from __future__ import annotations

import datetime as dt

from himawari_downloader.errors import ConfigurationError
from himawari_downloader.products.ftp_rules import acquisition_timedelta
from himawari_downloader.products.parse import group_remote_files


def normalize_timestamps(values: tuple[str | dt.datetime, ...]) -> list[dt.datetime]:
    output: list[dt.datetime] = []
    for value in values:
        if isinstance(value, dt.datetime):
            output.append(value)
        else:
            output.append(dt.datetime.fromisoformat(str(value).replace("T", " ")))
    return output


def select_latest_group(files, count: int):
    grouped = group_remote_files(files, key="start_time")
    keys = sorted(grouped)
    return {key: grouped[key] for key in keys[-count:]}


def select_closest_group(files, target_time: dt.datetime):
    grouped = group_remote_files(files, key="start_time")
    keys = sorted(grouped)
    if not keys:
        raise ConfigurationError("No files found for closest search.")
    closest = min(keys, key=lambda value: abs(value - target_time))
    return grouped[closest]


def select_previous_groups(files, start_time: dt.datetime, count: int, sector: str, include_start_time: bool, check_consistency: bool):
    grouped = group_remote_files(files, key="start_time")
    keys = sorted(grouped)
    keys = [key for key in keys if key <= start_time] if include_start_time else [key for key in keys if key < start_time]
    keys = keys[-count:]
    if len(keys) < count:
        raise ConfigurationError("Not enough previous timesteps available.")
    _check_regularity(keys, sector, check_consistency)
    return {key: grouped[key] for key in keys}


def select_next_groups(files, start_time: dt.datetime, count: int, sector: str, include_start_time: bool, check_consistency: bool):
    grouped = group_remote_files(files, key="start_time")
    keys = sorted(grouped)
    keys = [key for key in keys if key >= start_time] if include_start_time else [key for key in keys if key > start_time]
    keys = keys[:count]
    if len(keys) < count:
        raise ConfigurationError("Not enough next timesteps available.")
    _check_regularity(keys, sector, check_consistency)
    return {key: grouped[key] for key in keys}


def _check_regularity(keys: list[dt.datetime], sector: str, enabled: bool):
    if not enabled or len(keys) < 2:
        return
    step = acquisition_timedelta(sector)
    for previous, current in zip(keys[:-1], keys[1:]):
        if current - previous != step:
            raise ConfigurationError("The time interval is not regular.")
