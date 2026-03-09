from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from himawari_downloader import HimawariDownloader
from himawari_downloader.models import DownloadParams, NetcdfSubset, ProxyConfig, QueryParams


def _csv_tuple(text: str) -> tuple[str, ...]:
    if not text.strip():
        return ()
    return tuple(item.strip() for item in text.split(",") if item.strip())


def _pair(text: str) -> tuple[float, float] | None:
    if not text.strip():
        return None
    left, right = [float(item.strip()) for item in text.split(",", 1)]
    return (left, right)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Himawari downloader CLI")
    parser.add_argument("--ftp-user", default="")
    parser.add_argument("--ftp-password", default="")
    parser.add_argument("--ftp-host", default="ftp.ptree.jaxa.jp")
    parser.add_argument("--ftp-root", default="/jma")

    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ["find", "download", "latest", "closest", "previous", "next"]:
        sub = subparsers.add_parser(name)
        sub.add_argument("--source", required=True, choices=["ftp", "s3"])
        sub.add_argument("--satellite", required=True)
        sub.add_argument("--product-level", required=True)
        sub.add_argument("--product", required=True)
        sub.add_argument("--sector", required=True)
        sub.add_argument("--mode", default="range")
        sub.add_argument("--data-format", default="")
        sub.add_argument("--links", default="")
        sub.add_argument("--timestamps", default="")
        sub.add_argument("--dates", default="")
        sub.add_argument("--date-start", default="")
        sub.add_argument("--date-end", default="")
        sub.add_argument("--target-time", default="")
        sub.add_argument("--count", type=int, default=1)
        sub.add_argument("--utc-hours", default="00-08")
        sub.add_argument("--minute-step", type=float, default=None)
        sub.add_argument("--bands", default="")
        sub.add_argument("--scene-abbr", default="")
        sub.add_argument("--include-start-time", action="store_true")
        sub.add_argument("--proxy", default="")
        sub.add_argument("--proxy-ftp", default="")
        sub.add_argument("--proxy-s3", default="")
        sub.add_argument("--out-dir", default="data/out")
        sub.add_argument("--bbox-lat", default="")
        sub.add_argument("--bbox-lon", default="")
        sub.add_argument("--target-vars", default="tbb_07,tbb_14")
        sub.add_argument("--whole-file", action="store_true")
        sub.add_argument("--max-workers", type=int, default=4)
        sub.add_argument("--retries", type=int, default=1)
        sub.add_argument("--retry-wait-sec", type=float, default=1.0)
        sub.add_argument("--ftp-block-size", type=int, default=8 * 1024 * 1024)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    downloader = HimawariDownloader(
        ftp_user=args.ftp_user,
        ftp_password=args.ftp_password,
        ftp_host=args.ftp_host,
        ftp_root=args.ftp_root,
    )

    query = QueryParams(
        source=args.source,
        satellite=args.satellite,
        product_level=args.product_level,
        product=args.product,
        sector=args.sector,
        mode=_resolve_mode(args.command, args.mode),
        data_format=args.data_format or None,
        remote_files=_csv_tuple(args.links),
        timestamps=_csv_tuple(args.timestamps),
        dates=_csv_tuple(args.dates),
        date_start=args.date_start or None,
        date_end=args.date_end or None,
        target_time=args.target_time or None,
        count=args.count,
        utc_hours=args.utc_hours,
        minute_step=args.minute_step,
        bands=_csv_tuple(args.bands),
        scene_abbr=_csv_tuple(args.scene_abbr),
        include_start_time=args.include_start_time,
    )

    params = DownloadParams(
        out_dir=Path(args.out_dir),
        max_workers=args.max_workers,
        retries=args.retries,
        retry_wait_sec=args.retry_wait_sec,
        proxy=_build_proxy(args),
        ftp_block_size=args.ftp_block_size,
        netcdf_subset=_build_subset(args),
    )

    if args.command == "find":
        files = downloader.find_files(query)
        print(json.dumps([_remote_to_json(item) for item in files], ensure_ascii=False, indent=2))
        return
    if args.command == "download":
        result = downloader.download(query, params)
        print(json.dumps(_result_to_json(result), ensure_ascii=False, indent=2))
        return
    if args.command == "latest":
        files = downloader.find_latest(query)
        print(json.dumps([_remote_to_json(item) for item in files], ensure_ascii=False, indent=2))
        return
    if args.command == "closest":
        files = downloader.find_closest(query)
        print(json.dumps([_remote_to_json(item) for item in files], ensure_ascii=False, indent=2))
        return
    if args.command == "previous":
        grouped = downloader.find_previous(query)
        print(json.dumps({key.isoformat(): [_remote_to_json(item) for item in values] for key, values in grouped.items()}, ensure_ascii=False, indent=2))
        return
    grouped = downloader.find_next(query)
    print(json.dumps({key.isoformat(): [_remote_to_json(item) for item in values] for key, values in grouped.items()}, ensure_ascii=False, indent=2))


def _resolve_mode(command: str, explicit: str) -> str:
    if command in {"latest", "closest", "previous", "next"}:
        return command
    return explicit


def _build_proxy(args) -> ProxyConfig | None:
    if not args.proxy and not args.proxy_ftp and not args.proxy_s3:
        return None
    default = args.proxy or args.proxy_ftp or args.proxy_s3
    overrides = {}
    if args.proxy_ftp:
        overrides["ftp"] = args.proxy_ftp
    if args.proxy_s3:
        overrides["s3"] = args.proxy_s3
    return ProxyConfig(url=default, source_overrides=overrides)


def _build_subset(args) -> NetcdfSubset | None:
    bbox_lat = _pair(args.bbox_lat)
    bbox_lon = _pair(args.bbox_lon)
    if not bbox_lat and not bbox_lon and not args.whole_file:
        return None
    if args.source != "ftp" or (args.data_format or "").lower() != "netcdf":
        raise ValueError("bbox and whole-file options are supported only for ftp netcdf downloads.")
    return NetcdfSubset(
        bbox_lat=bbox_lat,
        bbox_lon=bbox_lon,
        target_vars=_csv_tuple(args.target_vars) or ("tbb_07", "tbb_14"),
        whole_file=args.whole_file,
    )


def _remote_to_json(item):
    data = asdict(item)
    data["start_time"] = item.start_time.isoformat()
    data["end_time"] = item.end_time.isoformat()
    return data


def _result_to_json(result):
    return {
        "saved_paths": [str(path) for path in result.saved_paths],
        "skipped_paths": [str(path) for path in result.skipped_paths],
        "missing_files": list(result.missing_files),
        "failed_files": list(result.failed_files),
    }
