from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict

from himawari_downloader.models import RemoteFile

FTP_NETCDF_RE = re.compile(
    r"NC_(?P<satellite>H\d{2})_(?P<ymd>\d{8})_(?P<hhmm>\d{4})_(?P<version>R\d{2}|r\d{2})_FLDK\.(?P<res>\d{5}_\d{5})\.nc$"
)
FTP_HSD_RE = re.compile(
    r"HS_(?P<satellite>H\d{2})_(?P<ymd>\d{8})_(?P<hhmm>\d{4})_B(?P<band>\d{2})_(?P<sector_code>FLDK|JP\d{2}|R\d{3})_R(?P<res>\d{2})_(?P<segment>S\d{4})\.DAT(?:\.bz2)?$"
)
S3_L2_RE = re.compile(
    r"AHI-(?P<product>[A-Z]+)(?:_[A-Za-z0-9]+)?_(?P<satellite>h\d{2})_s(?P<start>\d{15})_e(?P<end>\d{15})_c\d{15}\.nc$",
    re.IGNORECASE,
)

S3_PRODUCT_ALIASES = {
    "CLOUD_MASK": "CMSK",
    "CMSK": "CMSK",
    "CHGT": "CHGT",
    "CLOUD_HEIGHT": "CHGT",
    "CPHS": "CPHS",
    "CLOUD_PHASE": "CPHS",
    "RRQPE": "RRQPE",
    "HYDRO_RAIN_RATE": "RRQPE",
}


def _sector_from_code(code: str) -> tuple[str, str | None, dt.timedelta]:
    if code == "FLDK":
        return "FLDK", None, dt.timedelta(0)
    if code.startswith("JP"):
        obs = int(code[2:])
        return "Japan", "R2" if obs >= 3 else "R1", dt.timedelta(minutes=2, seconds=30) * (obs - 1)
    if code.startswith("R3"):
        obs = int(code[2:])
        return "Target", "R3", dt.timedelta(minutes=2, seconds=30) * (obs - 1)
    if code.startswith("R4"):
        obs = int(code[2:])
        return "Landmark", "R4", dt.timedelta(seconds=30) * (obs - 1)
    if code.startswith("R5"):
        obs = int(code[2:])
        return "Landmark", "R5", dt.timedelta(seconds=30) * (obs - 1)
    raise ValueError(f"Unsupported sector code: {code}")


def parse_remote_file(source: str, remote_path: str) -> RemoteFile:
    name = remote_path.replace("\\", "/").split("/")[-1]

    match = FTP_NETCDF_RE.match(name)
    if match:
        start = dt.datetime.strptime(f"{match.group('ymd')}{match.group('hhmm')}", "%Y%m%d%H%M")
        satellite = _normalize_satellite(match.group("satellite"))
        sector = "Japan" if match.group("version").startswith("r") else "FLDK"
        return RemoteFile(
            source=source,
            remote_path=remote_path,
            satellite=satellite,
            product_level="L2",
            product="NetCDF",
            sector=sector,
            start_time=start,
            end_time=start + dt.timedelta(minutes=10),
            spatial_res=match.group("res"),
            format="netcdf",
        )

    match = FTP_HSD_RE.match(name)
    if match:
        base_start = dt.datetime.strptime(f"{match.group('ymd')}{match.group('hhmm')}", "%Y%m%d%H%M")
        sector, scene_abbr, offset = _sector_from_code(match.group("sector_code"))
        start = base_start + offset
        duration = dt.timedelta(minutes=10) if sector == "FLDK" else (dt.timedelta(minutes=2, seconds=30) if sector in {"Japan", "Target"} else dt.timedelta(seconds=30))
        return RemoteFile(
            source=source,
            remote_path=remote_path,
            satellite=_normalize_satellite(match.group("satellite")),
            product_level="L1B",
            product="Rad",
            sector=sector,
            start_time=start,
            end_time=start + duration,
            band=f"B{match.group('band')}",
            scene_abbr=scene_abbr,
            spatial_res=match.group("res"),
            format="hsd",
        )

    match = S3_L2_RE.match(name)
    if match:
        start = dt.datetime.strptime(match.group("start")[:14], "%Y%m%d%H%M%S")
        end = dt.datetime.strptime(match.group("end")[:14], "%Y%m%d%H%M%S")
        satellite = f"HIMAWARI-{match.group('satellite')[-1]}"
        product = S3_PRODUCT_ALIASES.get(match.group("product").upper(), match.group("product").upper())
        return RemoteFile(
            source=source,
            remote_path=remote_path,
            satellite=satellite,
            product_level="L2",
            product=product,
            sector="FLDK",
            start_time=start,
            end_time=end,
            format="netcdf",
        )

    raise ValueError(f"Unsupported file name: {name}")


def group_remote_files(files: list[RemoteFile], key: str = "start_time") -> dict[object, list[RemoteFile]]:
    grouped: dict[object, list[RemoteFile]] = defaultdict(list)
    for item in sorted(files, key=lambda x: getattr(x, key)):
        grouped[getattr(item, key)].append(item)
    return dict(grouped)


def _normalize_satellite(value: str) -> str:
    text = value.upper()
    if text == "H08":
        return "HIMAWARI-8"
    if text == "H09":
        return "HIMAWARI-9"
    raise ValueError(f"Unsupported satellite code: {value}")
