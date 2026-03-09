from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RemoteFile:
    source: str
    remote_path: str
    satellite: str
    product_level: str
    product: str
    sector: str
    start_time: dt.datetime
    end_time: dt.datetime
    band: str | None = None
    scene_abbr: str | None = None
    spatial_res: str | None = None
    format: str = "other"


@dataclass(frozen=True)
class ProxyConfig:
    url: str
    username: str | None = None
    password: str | None = None
    bypass_hosts: tuple[str, ...] = ()
    source_overrides: dict[str, str] = field(default_factory=dict)

    def resolve_for_source(self, source: str) -> str:
        return self.source_overrides.get(source, self.url)


@dataclass(frozen=True)
class NetcdfSubset:
    bbox_lat: tuple[float, float] | None = None
    bbox_lon: tuple[float, float] | None = None
    target_vars: tuple[str, ...] = ("tbb_07", "tbb_14")
    whole_file: bool = False
    compression_level: int = 0
    fallback_full_download: bool = False


@dataclass(frozen=True)
class QueryParams:
    source: str
    satellite: str
    product_level: str
    product: str
    sector: str
    mode: str = "range"
    data_format: str | None = None
    remote_files: tuple[str, ...] = ()
    timestamps: tuple[str | dt.datetime, ...] = ()
    dates: tuple[str | dt.date, ...] = ()
    date_start: str | dt.date | None = None
    date_end: str | dt.date | None = None
    target_time: str | dt.datetime | None = None
    count: int = 1
    utc_hours: str = "00-08"
    minute_step: float | None = None
    bands: tuple[str, ...] = ()
    scene_abbr: tuple[str, ...] = ()
    include_start_time: bool = False
    check_consistency: bool = True


@dataclass(frozen=True)
class DownloadParams:
    out_dir: str | Path
    max_workers: int = 4
    retries: int = 1
    retry_wait_sec: float = 1.0
    skip_existing: bool = True
    check_integrity: bool = True
    show_progress: bool = True
    proxy: ProxyConfig | None = None
    ftp_block_size: int = 8 * 1024 * 1024
    netcdf_subset: NetcdfSubset | None = None


@dataclass(frozen=True)
class DownloadResult:
    saved_paths: tuple[Path, ...]
    skipped_paths: tuple[Path, ...]
    missing_files: tuple[str, ...]
    failed_files: tuple[str, ...]
