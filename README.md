# himawari-downloader

[English](README.md) | [简体中文](README.zh-CN.md)

[![PyPI version](https://img.shields.io/pypi/v/himawari-downloader.svg)](https://pypi.org/project/himawari-downloader/)
[![Python versions](https://img.shields.io/pypi/pyversions/himawari-downloader.svg)](https://pypi.org/project/himawari-downloader/)
[![CI](https://github.com/P-Coke/himawari-downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/P-Coke/himawari-downloader/actions/workflows/ci.yml)
[![Publish PyPI](https://github.com/P-Coke/himawari-downloader/actions/workflows/publish-pypi.yml/badge.svg)](https://github.com/P-Coke/himawari-downloader/actions/workflows/publish-pypi.yml)
[![License](https://img.shields.io/pypi/l/himawari-downloader.svg)](https://github.com/P-Coke/himawari-downloader/blob/main/LICENSE)

`himawari-downloader` is a Python SDK and CLI for querying and downloading Himawari-8/9 data from FTP and S3.

## Quick Links

| English | 简体中文 |
| --- | --- |
| [README](README.md) | [中文说明](README.zh-CN.md) |
| [Tutorial](docs/TUTORIAL.md) | [中文教程](docs/TUTORIAL.zh-CN.md) |
| [GitHub repository](https://github.com/P-Coke/himawari-downloader) | [PyPI package](https://pypi.org/project/himawari-downloader/) |

## Documentation

- [Installation](#installation)
- [Python usage](#python-usage)
- [Band mapping and parameter quick reference](#band-mapping-and-parameter-quick-reference)
- [CLI](#cli)
- [English tutorial](docs/TUTORIAL.md)
- [简体中文教程](docs/TUTORIAL.zh-CN.md)
- [FAQ, capability matrix, and cookbook](docs/TUTORIAL.md#11-faq-and-common-errors)

## Features

- Unified `HimawariDownloader` API
- Query modes: `find`, `latest`, `closest`, `previous`, `next`
- Download modes: `links`, `timestamps`, `dates`, `range`
- FTP support for `netcdf` and `hsd`
- FTP NetCDF remote bbox and variable subset download
- S3 file query and raw download
- Optional proxy support for FTP and S3

## What's New in v0.1.2

- FTP whole-file NetCDF downloads now use a direct FTP binary transfer path for better robustness.
- FTP NetCDF query candidates are filtered to existing remote files before being returned.
- Added download progress event support in the SDK (`DownloadEvent` and `DownloadParams.progress_callback`).
- NetCDF subset now supports full-disk variable export by combining:
  - `NetcdfSubset(whole_file=True, target_vars=(...))`

## Installation

Base install:

```bash
pip install himawari-downloader
```

Install S3 support:

```bash
pip install "himawari-downloader[s3]"
```

Install FTP NetCDF subset support:

```bash
pip install "himawari-downloader[ftp-netcdf]"
```

Install everything:

```bash
pip install "himawari-downloader[all]"
```

For local development:

```bash
pip install -e ".[dev]"
```

## Python usage

Basic FTP HSD download:

```python
from himawari_downloader import DownloadParams, HimawariDownloader, QueryParams

client = HimawariDownloader(ftp_user="your_uid", ftp_password="your_password")

query = QueryParams(
    source="ftp",
    satellite="H09",
    product_level="L1B",
    product="Rad",
    sector="FLDK",
    mode="dates",
    data_format="hsd",
    dates=("2025-03-19",),
    bands=("B07", "B14"),
)

result = client.download(query, DownloadParams(out_dir="data/out"))
print(result.saved_paths)
```

FTP NetCDF subset example:

```python
from himawari_downloader import DownloadParams, HimawariDownloader, NetcdfSubset, QueryParams

client = HimawariDownloader(ftp_user="your_uid", ftp_password="your_password")

query = QueryParams(
    source="ftp",
    satellite="H09",
    product_level="L2",
    product="NetCDF",
    sector="FLDK",
    mode="links",
    data_format="netcdf",
    remote_files=("/jma/netcdf/202503/19/NC_H09_20250319_0010_R21_FLDK.02401_02401.nc",),
)

result = client.download(
    query,
    DownloadParams(
        out_dir="data/out",
        netcdf_subset=NetcdfSubset(
            bbox_lat=(40.75, 34.44),
            bbox_lon=(110.27, 114.59),
            target_vars=("tbb_07",),
        ),
    ),
)

FTP NetCDF full-disk selected variable example:

```python
from himawari_downloader import DownloadParams, HimawariDownloader, NetcdfSubset, QueryParams

client = HimawariDownloader(ftp_user="your_uid", ftp_password="your_password")

query = QueryParams(
    source="ftp",
    satellite="H09",
    product_level="L2",
    product="NetCDF",
    sector="FLDK",
    mode="links",
    data_format="netcdf",
    remote_files=("/jma/netcdf/202503/19/NC_H09_20250319_0010_R21_FLDK.07001_06001.nc",),
)

result = client.download(
    query,
    DownloadParams(
        out_dir="data/out",
        netcdf_subset=NetcdfSubset(
            whole_file=True,
            target_vars=("tbb_07",),
        ),
    ),
)
```
```

Proxy example:

```python
from himawari_downloader import DownloadParams, ProxyConfig

params = DownloadParams(
    out_dir="data/out",
    proxy=ProxyConfig(
        url="http://127.0.0.1:7890",
        source_overrides={"s3": "http://127.0.0.1:7890"},
    ),
)
```

## Band mapping and parameter quick reference

Band and channel names:

- Use `B01` to `B16` in `bands`
- If you already know `C07`, `C14` style names from other tools, map them directly to `B07`, `B14`
- For FTP NetCDF subset download, use NetCDF variable names in `target_vars`, not `bands`

Typical NetCDF variable mapping:

- `B07` -> `tbb_07`
- `B14` -> `tbb_14`

Important `QueryParams` fields:

- `source`: `ftp` or `s3`
- `satellite`:
  - FTP examples usually use `H08` or `H09`
  - S3 examples usually use `HIMAWARI-8` or `HIMAWARI-9`
- `product_level`:
  - `L1B` for radiance segments
  - `L2` for derived products
- `product`:
  - FTP HSD usually uses `Rad`
  - FTP NetCDF currently uses `NetCDF`
  - S3 L2 examples include `CMSK`, `CHGT`, `CPHS`, `RRQPE`
- `sector`: `FLDK`, `Japan`, `Target`
- `data_format`: FTP only, `hsd` or `netcdf`
- `mode`: `links`, `timestamps`, `dates`, `range`, `latest`, `closest`, `previous`, `next`
- `bands`: tuple of `Bxx`, for example `("B07", "B14")`
- `scene_abbr`: optional regional scene filter like `R1`, `R2`, `R3`

Important `DownloadParams` fields:

- `out_dir`: output directory
- `max_workers`: number of concurrent downloads
- `retries`: retry count
- `skip_existing`: skip local files if they already exist
- `proxy`: `ProxyConfig(...)`
- `ftp_block_size`: FTP read block size
- `netcdf_subset`: FTP NetCDF subset configuration

Important `NetcdfSubset` fields:

- `bbox_lat`: latitude bounds
- `bbox_lon`: longitude bounds
- `target_vars`: NetCDF variable names such as `("tbb_07",)`
- `whole_file`: disable subsetting and download the entire file
- `compression_level`: output NetCDF compression level
- `fallback_full_download`: if subset download fails, try full download

Detailed tutorial:

- [English tutorial](docs/TUTORIAL.md)
- [简体中文教程](docs/TUTORIAL.zh-CN.md)

The tutorial also includes:

- product capability matrix
- cookbook recipes by task
- FAQ and common error guide

## CLI

```bash
himawari-download find \
  --source ftp \
  --satellite H09 \
  --product-level L1B \
  --product Rad \
  --sector FLDK \
  --mode dates \
  --data-format hsd \
  --dates 2025-03-19
```

More CLI and task-oriented examples are documented in:

- [English tutorial](docs/TUTORIAL.md)

## Test

```bash
python -m pytest -q
```

## Build

```bash
python -m build
python -m twine check dist/*
```

## Release

GitHub repository:

- `https://github.com/P-Coke/himawari-downloader`

PyPI publishing is configured through GitHub Actions trusted publishing.

To release:

1. Push changes to `main`
2. Create and push a version tag like `v0.1.0`
3. GitHub Actions will build and publish to PyPI

## Acknowledgments

This project was developed with design inspiration from
[`ghiggi/himawari_api`](https://github.com/ghiggi/himawari_api), especially around
Himawari file discovery workflows and query semantics such as `latest`,
`closest`, `previous`, and `next`.

`himawari_api` is distributed under the MIT License. This project is an
independent implementation and does not vendor or copy that codebase.
