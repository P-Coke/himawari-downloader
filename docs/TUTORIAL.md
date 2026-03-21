# Tutorial

[English](TUTORIAL.md) | [简体中文](TUTORIAL.zh-CN.md)

This guide explains band mapping and the main configuration parameters in `himawari-downloader`.

## Contents

- two kinds of names
- band mapping
- choosing FTP or S3
- product capability matrix
- `QueryParams`
- `DownloadParams`
- `NetcdfSubset`
- `ProxyConfig`
- recommended starting combinations
- cookbook
- FAQ and common errors

## 0. Changes in v0.1.2

- FTP whole-file NetCDF download now uses a direct FTP binary transfer path.
- FTP NetCDF query candidates are filtered to existing remote files before return.
- `DownloadParams` now supports progress callbacks through `progress_callback`.
- FTP NetCDF supports full-disk variable export via:
  - `NetcdfSubset(whole_file=True, target_vars=(...))`

## 1. Two kinds of names

Keep these two categories separate:

- Band names like `B07`, `B14`
- NetCDF variable names like `tbb_07`, `tbb_14`

Band names are used when selecting HSD or S3 L1 channels.
NetCDF variable names are used when subsetting FTP NetCDF files.

## 2. Band mapping

Recommended convention in this package:

- always pass `Bxx` in `bands`
- convert `Cxx` names from other tools to the matching `Bxx`

Examples:

- `C07` -> `B07`
- `C14` -> `B14`

Typical NetCDF variable mapping:

- `B07` -> `tbb_07`
- `B14` -> `tbb_14`

Examples:

```python
bands=("B07",)
bands=("B07", "B14")
target_vars=("tbb_07",)
target_vars=("tbb_07", "tbb_14")
```

## 3. Choosing FTP or S3

Use `source="ftp"` when:

- you want FTP HSD download
- you want FTP NetCDF download
- you want FTP NetCDF remote bbox/variable subset

Use `source="s3"` when:

- you want public NOAA S3 query or raw download
- you want `latest`, `closest`, `previous`, `next`

## 4. Product capability matrix

This table is the quickest way to see what is supported.

| Source | Product family | Query modes | Download | Remote subset | Notes |
| --- | --- | --- | --- | --- | --- |
| FTP | L1B HSD | `links`, `timestamps`, `dates`, `range` | Yes | No | Supports `bands`, segment and observation rules |
| FTP | NetCDF | `links`, `timestamps`, `dates`, `range` | Yes | Yes | Remote bbox and variable subset is FTP-only |
| S3 | L1 channels | `latest`, `closest`, `previous`, `next` | Yes | No | Raw file download only |
| S3 | L2 products such as `CMSK` | `latest`, `closest`, `previous`, `next` | Yes | No | Raw NetCDF download only |

Current practical examples:

- FTP HSD: `product_level="L1B"`, `product="Rad"`, `data_format="hsd"`
- FTP NetCDF: `product_level="L2"`, `product="NetCDF"`, `data_format="netcdf"`
- S3 cloud mask: `product_level="L2"`, `product="CMSK"`

Not supported in the current package:

- S3 remote NetCDF bbox subset
- FTP `latest`, `closest`, `previous`, `next`
- scene generation, satpy preprocessing, image rendering

## 5. QueryParams

Required core fields:

- `source`
- `satellite`
- `product_level`
- `product`
- `sector`

Mode-specific fields:

- `mode="links"` -> use `remote_files`
- `mode="timestamps"` -> use `timestamps`
- `mode="dates"` -> use `dates`
- `mode="range"` -> use `date_start` and `date_end`
- `mode="closest"` -> use `target_time`
- `mode="previous"` or `mode="next"` -> use `target_time` and optional `count`

Other useful fields:

- `data_format`: FTP only, `hsd` or `netcdf`
- `bands`: tuple of `Bxx`
- `scene_abbr`: optional scene filter like `("R1",)`
- `utc_hours`: hour range string like `"00-08"`
- `minute_step`: only needed if you want to be explicit
- `include_start_time`: used by `previous` and `next`
- `check_consistency`: used by `previous` and `next`

FTP HSD example:

```python
query = QueryParams(
    source="ftp",
    satellite="H09",
    product_level="L1B",
    product="Rad",
    sector="FLDK",
    mode="dates",
    data_format="hsd",
    dates=("2025-03-19",),
    bands=("B07",),
)
```

S3 L2 example:

```python
query = QueryParams(
    source="s3",
    satellite="HIMAWARI-9",
    product_level="L2",
    product="CMSK",
    sector="FLDK",
    mode="latest",
)
```

## 6. DownloadParams

Main fields:

- `out_dir`
- `max_workers`
- `retries`
- `retry_wait_sec`
- `skip_existing`
- `proxy`
- `ftp_block_size`
- `netcdf_subset`

Example:

```python
params = DownloadParams(
    out_dir="data/out",
    max_workers=4,
    retries=2,
)
```

## 7. NetcdfSubset

Use `NetcdfSubset` only with:

- `source="ftp"`
- `data_format="netcdf"`

Main fields:

- `bbox_lat`
- `bbox_lon`
- `target_vars`
- `whole_file`
- `compression_level`
- `fallback_full_download`
- `whole_file=True` with `target_vars=(...)` can be used to export selected variables without bbox cropping

Example:

```python
subset = NetcdfSubset(
    bbox_lat=(40.75, 34.44),
    bbox_lon=(110.27, 114.59),
    target_vars=("tbb_07",),
)
```

Full-disk selected variables example:

```python
subset = NetcdfSubset(
    whole_file=True,
    target_vars=("tbb_07", "tbb_14"),
)
```

## 8. ProxyConfig

Single shared proxy:

```python
proxy = ProxyConfig(url="http://127.0.0.1:7890")
```

Per-source override:

```python
proxy = ProxyConfig(
    url="http://127.0.0.1:7890",
    source_overrides={
        "s3": "http://127.0.0.1:7890",
        "ftp": "http://127.0.0.1:7890",
    },
)
```

Notes:

- `s3` proxying is usually the most reliable with HTTP proxies
- `ftp` direct download works
- `ftp` through some HTTP proxies may fail or time out during remote NetCDF reads
- if you need maximum stability for FTP NetCDF, prefer direct connection

## 9. Recommended starting combinations

FTP HSD single band:

```python
QueryParams(
    source="ftp",
    satellite="H09",
    product_level="L1B",
    product="Rad",
    sector="FLDK",
    mode="dates",
    data_format="hsd",
    dates=("2025-03-19",),
    bands=("B07",),
)
```

FTP NetCDF subset:

```python
QueryParams(
    source="ftp",
    satellite="H09",
    product_level="L2",
    product="NetCDF",
    sector="FLDK",
    mode="links",
    data_format="netcdf",
    remote_files=("/jma/netcdf/202503/19/NC_H09_20250319_0010_R21_FLDK.02401_02401.nc",),
)
```

S3 latest L2 query:

```python
QueryParams(
    source="s3",
    satellite="HIMAWARI-9",
    product_level="L2",
    product="CMSK",
    sector="FLDK",
    mode="latest",
)
```

## 10. Cookbook

This section is organized by task instead of by API object.

### Download one FTP HSD band for a whole day

Use this when you want one or more standard L1B channels from JAXA FTP.

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
    bands=("B07",),
)

result = client.download(query, DownloadParams(out_dir="data/hsd_b07"))
print(result.saved_paths)
```

### Download multiple FTP HSD bands

```python
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
```

### Download a specific FTP NetCDF file and crop it

Use `target_vars` with NetCDF variable names, not `Bxx`.

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

params = DownloadParams(
    out_dir="data/ftp_subset",
    netcdf_subset=NetcdfSubset(
        bbox_lat=(40.75, 34.44),
        bbox_lon=(110.27, 114.59),
        target_vars=("tbb_07",),
    ),
)

result = client.download(query, params)
print(result.saved_paths)
```

### Download a whole FTP NetCDF file without subsetting

```python
params = DownloadParams(
    out_dir="data/ftp_full",
    netcdf_subset=NetcdfSubset(whole_file=True),
)
```

### Download full-disk FTP NetCDF with selected variables

```python
params = DownloadParams(
    out_dir="data/ftp_full_vars",
    netcdf_subset=NetcdfSubset(
        whole_file=True,
        target_vars=("tbb_07",),
    ),
)
```

### Query the latest S3 cloud mask and then download it

```python
from himawari_downloader import DownloadParams, HimawariDownloader, QueryParams

client = HimawariDownloader()

query = QueryParams(
    source="s3",
    satellite="HIMAWARI-9",
    product_level="L2",
    product="CMSK",
    sector="FLDK",
    mode="latest",
)

files = client.find_latest(query)
result = client.download_files(files, DownloadParams(out_dir="data/cmsk"))
print(result.saved_paths)
```

### Find the closest S3 file to a target time

```python
query = QueryParams(
    source="s3",
    satellite="HIMAWARI-8",
    product_level="L1B",
    product="Rad",
    sector="FLDK",
    mode="closest",
    target_time="2021-11-17 21:03:00",
    bands=("B07",),
)
```

### Get previous or next S3 files around a timestamp

```python
query = QueryParams(
    source="s3",
    satellite="HIMAWARI-8",
    product_level="L2",
    product="CMSK",
    sector="FLDK",
    mode="previous",
    target_time="2021-11-17 21:00:00",
    count=3,
)
```

Change `mode="previous"` to `mode="next"` to move forward in time.

### Use a shared proxy for both S3 and FTP

```python
from himawari_downloader import DownloadParams, ProxyConfig

params = DownloadParams(
    out_dir="data/out",
    proxy=ProxyConfig(url="http://127.0.0.1:7890"),
)
```

### Use different proxies for S3 and FTP

```python
params = DownloadParams(
    out_dir="data/out",
    proxy=ProxyConfig(
        url="http://127.0.0.1:7890",
        source_overrides={
            "s3": "http://127.0.0.1:7890",
            "ftp": "http://127.0.0.1:9981",
        },
    ),
)
```

### CLI example: find FTP files first

```bash
himawari-download find \
  --source ftp \
  --satellite H09 \
  --product-level L1B \
  --product Rad \
  --sector FLDK \
  --mode dates \
  --data-format hsd \
  --dates 2025-03-19 \
  --bands B07
```

### CLI example: download latest S3 cloud mask

```bash
himawari-download latest \
  --source s3 \
  --satellite HIMAWARI-9 \
  --product-level L2 \
  --product CMSK \
  --sector FLDK
```

## 11. FAQ and common errors

### What is the difference between `bands` and `target_vars`?

- `bands` is for band selection such as `("B07", "B14")`
- `target_vars` is for NetCDF variable names such as `("tbb_07", "tbb_14")`
- if you are cropping FTP NetCDF files, use `target_vars`

### Can I download S3 cloud mask data?

Yes. `source="s3"` with `product_level="L2"` and `product="CMSK"` is supported for query and raw download.

### Why does FTP NetCDF subset fail behind an HTTP proxy?

Common reasons:

- the proxy supports HTTP traffic well but is unstable for FTP reads
- remote NetCDF access performs multiple reads and can time out
- the proxy may not support the exact transport pattern used by the FTP client

What to do:

- try direct FTP first
- reduce concurrency
- increase retry count
- use whole-file download if you only need transfer stability

### Why do I get a dependency error for NetCDF subset?

The FTP NetCDF crop path requires the `ftp-netcdf` extra.

Install it with:

```bash
pip install "himawari-downloader[ftp-netcdf]"
```

Or install everything:

```bash
pip install "himawari-downloader[all]"
```

### Why do I get a dependency error for S3?

The S3 backend requires the `s3` extra.

```bash
pip install "himawari-downloader[s3]"
```

### Which satellite name should I use?

Recommended values in the current package:

- FTP: `H08`, `H09`
- S3: `HIMAWARI-8`, `HIMAWARI-9`

If you are switching between FTP and S3, do not assume the same satellite string works in both places.

### Why is `latest` not working for FTP?

`latest`, `closest`, `previous`, and `next` are currently implemented for `s3` query flows.
FTP currently uses `links`, `timestamps`, `dates`, and `range`.

### Why does my bbox subset return no data or a tiny file?

Common causes:

- latitude bounds are reversed for your intended region
- longitude bounds do not overlap the file coverage
- `target_vars` does not exist in the source NetCDF
- the selected region is very small

Check:

- the bbox values
- the file timestamp and sector
- the variable names in `target_vars`

### Which products are good first tests?

Recommended simple starting points:

- FTP HSD: `L1B` + `Rad` + `B07`
- FTP NetCDF crop: `NetCDF` + `tbb_07`
- FTP NetCDF full-disk selected vars: `NetCDF` + `whole_file=True` + `tbb_07`
- S3 L2: `CMSK`
