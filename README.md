# himawari-downloader

`himawari-downloader` is a Python SDK and CLI for querying and downloading Himawari-8/9 data from FTP and S3.

## Features

- Unified `HimawariDownloader` API
- Query modes: `find`, `latest`, `closest`, `previous`, `next`
- Download modes: `links`, `timestamps`, `dates`, `range`
- FTP support for `netcdf` and `hsd`
- FTP NetCDF remote bbox and variable subset download
- S3 file query and raw download
- Optional proxy support for FTP and S3

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
