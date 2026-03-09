from __future__ import annotations

import datetime as dt
from pathlib import Path

import fsspec

from himawari_downloader.backends.base import BaseBackend
from himawari_downloader.errors import ConfigurationError, RemoteFileNotFoundError
from himawari_downloader.models import DownloadParams, QueryParams, RemoteFile
from himawari_downloader.products.parse import group_remote_files, parse_remote_file
from himawari_downloader.query.timeline import select_closest_group, select_latest_group, select_next_groups, select_previous_groups
from himawari_downloader.transport import build_s3_fs_args


class S3Backend(BaseBackend):
    source = "s3"

    def __init__(self, *, fs_args: dict | None = None) -> None:
        self.fs_args = dict(fs_args or {})

    def find_files(self, query: QueryParams) -> list[RemoteFile]:
        mode = query.mode.lower()
        if mode == "links":
            return [parse_remote_file("s3", path) for path in query.remote_files]
        if mode in {"timestamps", "dates", "range"}:
            return self._find_time_window_files(query)
        if mode == "latest":
            return self.find_latest(query)
        if mode == "closest":
            return self.find_closest(query)
        if mode == "previous":
            grouped = self.find_previous(query)
            return [item for values in grouped.values() for item in values]
        if mode == "next":
            grouped = self.find_next(query)
            return [item for values in grouped.values() for item in values]
        raise ConfigurationError(f"Unsupported query mode: {query.mode}")

    def find_latest(self, query: QueryParams) -> list[RemoteFile]:
        files = self._find_time_window_files(self._prepare_recent_window(query, lookback_minutes=30))
        grouped = select_latest_group(files, max(query.count, 1))
        return grouped[sorted(grouped)[-1]]

    def find_closest(self, query: QueryParams) -> list[RemoteFile]:
        if query.target_time is None:
            raise ConfigurationError("closest mode requires target_time")
        target_time = self._to_datetime(query.target_time)
        files = self._find_time_window_files(self._prepare_explicit_window(query, target_time - self._acquisition_delta(query.sector), target_time + self._acquisition_delta(query.sector)))
        return select_closest_group(files, target_time)

    def find_previous(self, query: QueryParams) -> dict[dt.datetime, list[RemoteFile]]:
        if query.target_time is None:
            raise ConfigurationError("previous mode requires target_time")
        target_time = self._to_datetime(query.target_time)
        count = max(query.count, 1)
        files = self._find_time_window_files(self._prepare_explicit_window(query, target_time - self._acquisition_delta(query.sector) * (count + 1), target_time))
        return select_previous_groups(files, target_time, count, query.sector, query.include_start_time, query.check_consistency)

    def find_next(self, query: QueryParams) -> dict[dt.datetime, list[RemoteFile]]:
        if query.target_time is None:
            raise ConfigurationError("next mode requires target_time")
        target_time = self._to_datetime(query.target_time)
        count = max(query.count, 1)
        files = self._find_time_window_files(self._prepare_explicit_window(query, target_time, target_time + self._acquisition_delta(query.sector) * (count + 1)))
        return select_next_groups(files, target_time, count, query.sector, query.include_start_time, query.check_consistency)

    def download_file(self, remote_file: RemoteFile, params: DownloadParams) -> Path:
        out_dir = Path(params.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / remote_file.remote_path.replace("\\", "/").split("/")[-1]
        fs = self._get_fs(params)
        try:
            with fs.open(remote_file.remote_path, "rb") as src, open(out_path, "wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)
        except FileNotFoundError as exc:
            raise RemoteFileNotFoundError(remote_file.remote_path) from exc
        return out_path

    def _find_time_window_files(self, query: QueryParams) -> list[RemoteFile]:
        start_time, end_time = self._resolve_window(query)
        fs = self._get_fs()
        product_dir = self._get_product_dir(query)
        directories = self._time_directories(start_time, end_time)
        output: list[RemoteFile] = []
        wanted_bands = set(_normalize_query_bands(query.bands)) if query.bands else None
        wanted_scene = set(query.scene_abbr) if query.scene_abbr else None
        for directory in directories:
            pattern = f"{product_dir}/{directory}/*"
            for path in fs.glob(pattern):
                full_path = path if path.startswith("s3://") else f"s3://{path}"
                try:
                    item = parse_remote_file("s3", full_path)
                except ValueError:
                    continue
                if item.product_level.upper() != query.product_level.upper():
                    continue
                if query.product_level.upper() == "L2" and item.product.upper() != query.product.upper():
                    continue
                if wanted_bands and item.band not in wanted_bands:
                    continue
                if wanted_scene and item.scene_abbr not in wanted_scene:
                    continue
                if item.end_time <= start_time or item.start_time > end_time:
                    continue
                output.append(item)
        return _dedupe_l1_resolution(output)

    def _get_fs(self, params: DownloadParams | None = None):
        fs_args = dict(self.fs_args)
        fs_args.update(build_s3_fs_args(params.proxy if params is not None else None))
        return fsspec.filesystem("s3", **fs_args)

    @staticmethod
    def _get_product_dir(query: QueryParams) -> str:
        satellite = query.satellite.upper().replace("-", "")
        if query.product_level.upper() == "L1B":
            return f"s3://noaa-{satellite.lower()}/AHI-L1b-{query.sector}"
        suffix_map = {"CMSK": "Clouds", "CHGT": "Clouds", "CPHS": "Clouds", "RRQPE": "RainfallRate"}
        suffix = suffix_map.get(query.product.upper(), "Clouds")
        return f"s3://noaa-{satellite.lower()}/AHI-L2-{query.sector}-{suffix}"

    @staticmethod
    def _time_directories(start_time: dt.datetime, end_time: dt.datetime) -> list[str]:
        current = start_time.replace(minute=(start_time.minute // 10) * 10, second=0, microsecond=0)
        directories: list[str] = []
        while current <= end_time + dt.timedelta(minutes=10):
            directories.append(current.strftime("%Y/%m/%d/%H%M"))
            current += dt.timedelta(minutes=10)
        return directories

    @staticmethod
    def _resolve_window(query: QueryParams) -> tuple[dt.datetime, dt.datetime]:
        if query.mode == "timestamps":
            timestamps = [S3Backend._to_datetime(value) for value in query.timestamps]
            return min(timestamps), max(timestamps)
        if query.mode == "dates":
            if not query.dates:
                raise ConfigurationError("dates mode requires dates")
            dates = [S3Backend._to_date(value) for value in query.dates]
            return dt.datetime.combine(min(dates), dt.time.min), dt.datetime.combine(max(dates), dt.time(23, 59))
        if query.mode == "range":
            if query.date_start is None or query.date_end is None:
                raise ConfigurationError("range mode requires date_start and date_end")
            return dt.datetime.combine(S3Backend._to_date(query.date_start), dt.time.min), dt.datetime.combine(S3Backend._to_date(query.date_end), dt.time(23, 59))
        raise ConfigurationError(f"mode '{query.mode}' does not map to a time window")

    @staticmethod
    def _prepare_recent_window(query: QueryParams, lookback_minutes: int) -> QueryParams:
        now = dt.datetime.utcnow().replace(second=0, microsecond=0)
        return QueryParams(**{**query.__dict__, "mode": "range", "date_start": (now - dt.timedelta(minutes=lookback_minutes)).date(), "date_end": now.date()})

    @staticmethod
    def _prepare_explicit_window(query: QueryParams, start_time: dt.datetime, end_time: dt.datetime) -> QueryParams:
        return QueryParams(**{**query.__dict__, "mode": "timestamps", "timestamps": (start_time, end_time)})

    @staticmethod
    def _acquisition_delta(sector: str) -> dt.timedelta:
        if sector == "FLDK":
            return dt.timedelta(minutes=10)
        if sector in {"Japan", "Target"}:
            return dt.timedelta(minutes=2, seconds=30)
        return dt.timedelta(seconds=30)

    @staticmethod
    def _to_datetime(value: str | dt.datetime) -> dt.datetime:
        if isinstance(value, dt.datetime):
            return value
        return dt.datetime.fromisoformat(str(value).replace("T", " "))

    @staticmethod
    def _to_date(value: str | dt.date) -> dt.date:
        if isinstance(value, dt.datetime):
            return value.date()
        if isinstance(value, dt.date):
            return value
        return dt.datetime.strptime(str(value), "%Y-%m-%d").date()


def _normalize_query_bands(values: tuple[str, ...]) -> tuple[str, ...]:
    output = []
    for value in values:
        text = value.upper().replace("C", "B")
        if len(text) == 2:
            text = f"B0{text[-1]}"
        output.append(text)
    return tuple(output)


def _dedupe_l1_resolution(files: list[RemoteFile]) -> list[RemoteFile]:
    grouped = group_remote_files(files, key="start_time")
    selected: list[RemoteFile] = []
    for items in grouped.values():
        by_band: dict[str, list[RemoteFile]] = {}
        for item in items:
            by_band.setdefault(item.band or "", []).append(item)
        for candidates in by_band.values():
            if len(candidates) == 1:
                selected.extend(candidates)
            else:
                selected.append(sorted(candidates, key=lambda item: item.spatial_res or "99")[0])
    return sorted(selected, key=lambda item: (item.start_time, item.band or "", item.remote_path))
