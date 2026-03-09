from __future__ import annotations

import datetime as dt
import threading
from pathlib import Path

import fsspec

from himawari_downloader.backends.base import BaseBackend
from himawari_downloader.errors import ConfigurationError, RemoteFileNotFoundError, UnsupportedOperationError
from himawari_downloader.models import DownloadParams, QueryParams, RemoteFile
from himawari_downloader.products.ftp_rules import (
    HOUSEKEEPING_HHMM,
    JAPAN_NETCDF_BOUNDS,
    default_full_disk_segments,
    expected_minute_step,
    normalize_band,
    normalize_hsd_resolution,
    normalize_obs_no,
    parse_hours,
    to_date,
    to_datetime,
)
from himawari_downloader.products.parse import parse_remote_file
from himawari_downloader.transport import ftp_proxy_context


class FTPBackend(BaseBackend):
    source = "ftp"
    _tls = threading.local()

    def __init__(
        self,
        *,
        ftp_host: str = "ftp.ptree.jaxa.jp",
        ftp_root: str = "/jma",
        ftp_user: str | None = None,
        ftp_password: str | None = None,
        netcdf_full_res: str = "07001_06001",
        netcdf_japan_band: str = "14",
        hsd_resolution: str = "20",
        hsd_segments_full_disk: tuple[str, ...] | None = None,
        hsd_obs_numbers: tuple[str, ...] = ("01", "02", "03", "04"),
        hsd_extension: str = ".DAT.bz2",
    ) -> None:
        self.ftp_host = ftp_host
        self.ftp_root = ftp_root.rstrip("/")
        self.ftp_user = ftp_user or ""
        self.ftp_password = ftp_password or ""
        self.netcdf_full_res = netcdf_full_res
        self.netcdf_japan_band = normalize_band(netcdf_japan_band)
        self.hsd_resolution = normalize_hsd_resolution(hsd_resolution)
        self.hsd_segments_full_disk = tuple(hsd_segments_full_disk or default_full_disk_segments())
        self.hsd_obs_numbers = tuple(normalize_obs_no(value) for value in hsd_obs_numbers)
        self.hsd_extension = hsd_extension

    def find_files(self, query: QueryParams) -> list[RemoteFile]:
        data_format = self._get_data_format(query)
        sector = self._normalize_sector(query.sector)
        mode = query.mode.lower()
        if mode == "links":
            if not query.remote_files:
                raise ConfigurationError("mode='links' requires remote_files")
            paths = sorted(set(query.remote_files))
        elif mode == "timestamps":
            timestamps = [to_datetime(value) for value in query.timestamps]
            paths = self._build_candidates(query, data_format, sector, timestamps)
        elif mode == "dates":
            if not query.dates:
                raise ConfigurationError("mode='dates' requires dates")
            timestamps = self._expand_dates(data_format, sector, [to_date(value) for value in query.dates], query.utc_hours, query.minute_step)
            paths = self._build_candidates(query, data_format, sector, timestamps)
        elif mode == "range":
            if query.date_start is None or query.date_end is None:
                raise ConfigurationError("mode='range' requires date_start and date_end")
            start = to_date(query.date_start)
            end = to_date(query.date_end)
            if start > end:
                raise ConfigurationError("date_start must be <= date_end")
            dates: list[dt.date] = []
            current = start
            while current <= end:
                dates.append(current)
                current += dt.timedelta(days=1)
            timestamps = self._expand_dates(data_format, sector, dates, query.utc_hours, query.minute_step)
            paths = self._build_candidates(query, data_format, sector, timestamps)
        else:
            raise UnsupportedOperationError(f"FTP backend does not support mode '{query.mode}'.")
        return [parse_remote_file("ftp", path) for path in paths]

    def find_latest(self, query: QueryParams) -> list[RemoteFile]:
        raise UnsupportedOperationError("FTP backend supports only links/timestamps/dates/range.")

    def find_closest(self, query: QueryParams) -> list[RemoteFile]:
        raise UnsupportedOperationError("FTP backend supports only links/timestamps/dates/range.")

    def find_previous(self, query: QueryParams) -> dict[dt.datetime, list[RemoteFile]]:
        raise UnsupportedOperationError("FTP backend supports only links/timestamps/dates/range.")

    def find_next(self, query: QueryParams) -> dict[dt.datetime, list[RemoteFile]]:
        raise UnsupportedOperationError("FTP backend supports only links/timestamps/dates/range.")

    def download_file(self, remote_file: RemoteFile, params: DownloadParams) -> Path:
        out_dir = Path(params.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / self._output_name(remote_file.remote_path)
        with ftp_proxy_context(params.proxy):
            if remote_file.format == "netcdf":
                self._download_netcdf(remote_file.remote_path, out_path, params)
            else:
                self._download_binary(remote_file.remote_path, out_path, params)
        return out_path

    def _expand_dates(self, data_format: str, sector: str, dates: list[dt.date], utc_hours: str, minute_step: float | None) -> list[dt.datetime]:
        hours = parse_hours(utc_hours)
        expected = expected_minute_step(data_format, sector)
        step = expected if minute_step is None else float(minute_step)
        if step != expected:
            raise ConfigurationError(f"minute_step for format={data_format}, sector={sector} must be {expected}")
        items: list[dt.datetime] = []
        for date in dates:
            for hour in hours:
                for minute in range(0, 60, 10):
                    hhmm = f"{hour:02d}{minute:02d}"
                    if hhmm in HOUSEKEEPING_HHMM:
                        continue
                    items.append(dt.datetime.combine(date, dt.time(hour, minute)))
        return items

    def _build_candidates(self, query: QueryParams, data_format: str, sector: str, timestamps: list[dt.datetime]) -> list[str]:
        satellite = self._normalize_satellite(query.satellite)
        bands = tuple(normalize_band(value) for value in (query.bands or ("B07", "B14")))
        paths: list[str] = []
        for timestamp in timestamps:
            ymd = timestamp.strftime("%Y%m%d")
            yyyymm = timestamp.strftime("%Y%m")
            dd = timestamp.strftime("%d")
            hh = timestamp.strftime("%H")
            hhmm = timestamp.strftime("%H%M")
            if data_format == "netcdf":
                if sector == "FLDK":
                    name = f"NC_{satellite}_{ymd}_{hhmm}_R21_FLDK.{self.netcdf_full_res}.nc"
                elif sector == "Japan":
                    name = f"NC_{satellite}_{ymd}_{hhmm}_r{self.netcdf_japan_band}_FLDK.02701_02601.nc"
                else:
                    raise ConfigurationError("FTP netcdf supports only FLDK and Japan sectors.")
                paths.append(f"{self.ftp_root}/netcdf/{yyyymm}/{dd}/{name}")
                continue
            if sector == "FLDK":
                for band in bands:
                    for segment in self.hsd_segments_full_disk:
                        name = f"HS_{satellite}_{ymd}_{hhmm}_B{band}_FLDK_R{self.hsd_resolution}_{segment}{self.hsd_extension}"
                        paths.append(f"{self.ftp_root}/hsd/{yyyymm}/{dd}/{hh}/{name}")
            elif sector == "Japan":
                for obs_no in self.hsd_obs_numbers:
                    for band in bands:
                        name = f"HS_{satellite}_{ymd}_{hhmm}_B{band}_JP{obs_no}_R{self.hsd_resolution}_S0101{self.hsd_extension}"
                        paths.append(f"{self.ftp_root}/hsd/{yyyymm}/{dd}/{hh}/{name}")
            elif sector == "Target":
                for obs_no in self.hsd_obs_numbers:
                    for band in bands:
                        name = f"HS_{satellite}_{ymd}_{hhmm}_B{band}_R3{obs_no}_R{self.hsd_resolution}_S0101{self.hsd_extension}"
                        paths.append(f"{self.ftp_root}/hsd/{yyyymm}/{dd}/{hh}/{name}")
            else:
                raise ConfigurationError("FTP HSD supports only FLDK, Japan and Target sectors.")
        return sorted(set(paths))

    def _download_netcdf(self, remote: str, out_path: Path, params: DownloadParams) -> None:
        xr = _require_xarray()
        subset = params.netcdf_subset
        if subset is None or subset.whole_file:
            self._download_binary(remote, out_path, params)
            return
        if subset.bbox_lat is None or subset.bbox_lon is None:
            raise ConfigurationError("NetCDF subset requires bbox_lat and bbox_lon.")
        self._validate_japan_bbox(remote, subset.bbox_lat, subset.bbox_lon)
        fs = self._get_fs()
        with self._open(fs, remote, params) as file_obj:
            ds = xr.open_dataset(file_obj, engine="h5netcdf", chunks={}, decode_timedelta=False)
            try:
                if "latitude" not in ds.coords or "longitude" not in ds.coords:
                    raise ConfigurationError("latitude/longitude coordinates not found")
                variables = [name for name in subset.target_vars if name in ds.variables]
                if not variables:
                    raise ConfigurationError("No target variables found in dataset.")
                sliced = self._subset_by_bbox(ds[variables], subset.bbox_lat, subset.bbox_lon)
                if subset.compression_level > 0:
                    encoding = {name: {"zlib": True, "complevel": subset.compression_level} for name in sliced.data_vars}
                    sliced.to_netcdf(out_path, engine="h5netcdf", encoding=encoding)
                else:
                    sliced.to_netcdf(out_path, engine="h5netcdf")
            except Exception:
                if subset.fallback_full_download:
                    self._download_binary(remote, out_path.with_name(out_path.stem + "_full.nc"), params)
                    return
                raise
            finally:
                ds.close()

    def _subset_by_bbox(self, ds, bbox_lat: tuple[float, float], bbox_lon: tuple[float, float]):
        np = _require_numpy()
        lat = np.asarray(ds["latitude"].values)
        lon = np.asarray(ds["longitude"].values)
        lat_min, lat_max = min(bbox_lat), max(bbox_lat)
        lon_min, lon_max = min(bbox_lon), max(bbox_lon)
        lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
        lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]
        if lat_idx.size == 0 or lon_idx.size == 0:
            raise ConfigurationError("bbox is outside coordinates")
        return ds.isel(
            latitude=slice(int(lat_idx.min()), int(lat_idx.max()) + 1),
            longitude=slice(int(lon_idx.min()), int(lon_idx.max()) + 1),
        )

    def _download_binary(self, remote: str, out_path: Path, params: DownloadParams) -> None:
        fs = self._get_fs()
        try:
            with self._open(fs, remote, params) as src, open(out_path, "wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)
        except FileNotFoundError as exc:
            raise RemoteFileNotFoundError(remote) from exc
        except Exception as exc:
            if "550" in str(exc) or "No such file" in str(exc):
                raise RemoteFileNotFoundError(remote) from exc
            raise

    def _get_fs(self) -> fsspec.AbstractFileSystem:
        key = f"{self.ftp_host}|{self.ftp_user}"
        if getattr(self._tls, "fs_key", None) != key or not hasattr(self._tls, "fs"):
            self._tls.fs = fsspec.filesystem("ftp", host=self.ftp_host, username=self.ftp_user, password=self.ftp_password)
            self._tls.fs_key = key
        return self._tls.fs

    @staticmethod
    def _open(fs: fsspec.AbstractFileSystem, remote: str, params: DownloadParams):
        if params.ftp_block_size <= 0:
            return fs.open(remote, mode="rb")
        try:
            return fs.open(remote, mode="rb", block_size=params.ftp_block_size, cache_type="readahead")
        except TypeError:
            return fs.open(remote, mode="rb", block_size=params.ftp_block_size)

    @staticmethod
    def _output_name(remote: str) -> str:
        return remote.replace("\\", "/").split("/")[-1]

    @staticmethod
    def _normalize_satellite(value: str) -> str:
        text = value.upper().replace("HIMAWARI-", "H")
        if text not in {"H08", "H09"}:
            raise ConfigurationError("FTP backend supports H08 and H09 satellites only.")
        return text

    @staticmethod
    def _normalize_sector(value: str) -> str:
        mapping = {"FULL_DISK": "FLDK", "FLDK": "FLDK", "JAPAN": "Japan", "TARGET": "Target"}
        normalized = mapping.get(value.upper(), value)
        if normalized not in {"FLDK", "Japan", "Target"}:
            raise ConfigurationError("FTP backend supports FLDK, Japan and Target sectors only.")
        return normalized

    @staticmethod
    def _get_data_format(query: QueryParams) -> str:
        if query.data_format is None:
            raise ConfigurationError("FTP queries require data_format='netcdf' or 'hsd'.")
        data_format = query.data_format.strip().lower()
        if data_format not in {"netcdf", "hsd"}:
            raise ConfigurationError("data_format must be 'netcdf' or 'hsd'")
        return data_format

    @staticmethod
    def _validate_japan_bbox(remote: str, bbox_lat: tuple[float, float], bbox_lon: tuple[float, float]) -> None:
        if "_r" not in remote:
            return
        lat_min, lat_max = min(bbox_lat), max(bbox_lat)
        lon_min, lon_max = min(bbox_lon), max(bbox_lon)
        if lat_min < JAPAN_NETCDF_BOUNDS["lat_min"] or lat_max > JAPAN_NETCDF_BOUNDS["lat_max"]:
            raise ConfigurationError("NetCDF Japan bbox exceeds 24N-50N")
        if lon_min < JAPAN_NETCDF_BOUNDS["lon_min"] or lon_max > JAPAN_NETCDF_BOUNDS["lon_max"]:
            raise ConfigurationError("NetCDF Japan bbox exceeds 123E-150E")


def _require_numpy():
    try:
        import numpy as np
    except ImportError as exc:
        raise ConfigurationError(
            "FTP NetCDF subsetting requires optional dependency group 'ftp-netcdf'. "
            "Install with: pip install himawari-downloader[ftp-netcdf]"
        ) from exc
    return np


def _require_xarray():
    try:
        import xarray as xr
    except ImportError as exc:
        raise ConfigurationError(
            "FTP NetCDF subsetting requires optional dependency group 'ftp-netcdf'. "
            "Install with: pip install himawari-downloader[ftp-netcdf]"
        ) from exc
    return xr
