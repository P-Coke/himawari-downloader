# himawari-downloader

[English](README.md) | [简体中文](README.zh-CN.md)

[![PyPI version](https://img.shields.io/pypi/v/himawari-downloader.svg)](https://pypi.org/project/himawari-downloader/)
[![Python versions](https://img.shields.io/pypi/pyversions/himawari-downloader.svg)](https://pypi.org/project/himawari-downloader/)
[![CI](https://github.com/P-Coke/himawari-downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/P-Coke/himawari-downloader/actions/workflows/ci.yml)
[![Publish PyPI](https://github.com/P-Coke/himawari-downloader/actions/workflows/publish-pypi.yml/badge.svg)](https://github.com/P-Coke/himawari-downloader/actions/workflows/publish-pypi.yml)
[![License](https://img.shields.io/pypi/l/himawari-downloader.svg)](https://github.com/P-Coke/himawari-downloader/blob/main/LICENSE)

`himawari-downloader` 是一个用于查询和下载 Himawari-8/9 卫星数据的 Python SDK 和 CLI，支持 FTP 与 S3 两类数据源。

## 快速入口

| English | 简体中文 |
| --- | --- |
| [README](README.md) | [中文说明](README.zh-CN.md) |
| [Tutorial](docs/TUTORIAL.md) | [中文教程](docs/TUTORIAL.zh-CN.md) |
| [GitHub repository](https://github.com/P-Coke/himawari-downloader) | [PyPI package](https://pypi.org/project/himawari-downloader/) |

## 文档导航

- [安装](#安装)
- [Python 使用示例](#python-使用示例)
- [波段映射与参数速查](#波段映射与参数速查)
- [CLI](#cli)
- [English tutorial](docs/TUTORIAL.md)
- [简体中文教程](docs/TUTORIAL.zh-CN.md)
- [FAQ、能力矩阵与 cookbook](docs/TUTORIAL.zh-CN.md#11-faq-与常见报错)

## 功能特性

- 统一的 `HimawariDownloader` API
- 查询模式：`find`、`latest`、`closest`、`previous`、`next`
- 下载模式：`links`、`timestamps`、`dates`、`range`
- FTP 支持 `netcdf` 与 `hsd`
- FTP NetCDF 远程 bbox 和变量裁剪下载
- S3 文件查询与原始文件下载
- FTP 与 S3 的可选代理支持

## 安装

基础安装：

```bash
pip install himawari-downloader
```

安装 S3 支持：

```bash
pip install "himawari-downloader[s3]"
```

安装 FTP NetCDF 裁剪支持：

```bash
pip install "himawari-downloader[ftp-netcdf]"
```

安装完整功能：

```bash
pip install "himawari-downloader[all]"
```

本地开发安装：

```bash
pip install -e ".[dev]"
```

## Python 使用示例

基础 FTP HSD 下载：

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

FTP NetCDF 裁剪示例：

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

代理配置示例：

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

## 波段映射与参数速查

波段和通道名：

- 在 `bands` 中使用 `B01` 到 `B16`
- 如果你来自其他工具，常见的 `C07`、`C14` 可以直接映射为 `B07`、`B14`
- 对 FTP NetCDF 裁剪下载，应在 `target_vars` 中填写 NetCDF 变量名，而不是 `bands`

常见 NetCDF 变量映射：

- `B07` -> `tbb_07`
- `B14` -> `tbb_14`

重要的 `QueryParams` 字段：

- `source`：`ftp` 或 `s3`
- `satellite`：
  - FTP 示例通常使用 `H08` 或 `H09`
  - S3 示例通常使用 `HIMAWARI-8` 或 `HIMAWARI-9`
- `product_level`：
  - `L1B` 表示辐射观测数据
  - `L2` 表示派生产品
- `product`：
  - FTP HSD 通常使用 `Rad`
  - FTP NetCDF 当前使用 `NetCDF`
  - S3 L2 示例包括 `CMSK`、`CHGT`、`CPHS`、`RRQPE`
- `sector`：`FLDK`、`Japan`、`Target`
- `data_format`：仅 FTP 使用，支持 `hsd` 或 `netcdf`
- `mode`：`links`、`timestamps`、`dates`、`range`、`latest`、`closest`、`previous`、`next`
- `bands`：`Bxx` 组成的元组，例如 `("B07", "B14")`
- `scene_abbr`：可选的区域场景过滤，如 `R1`、`R2`、`R3`

重要的 `DownloadParams` 字段：

- `out_dir`：输出目录
- `max_workers`：并发下载数量
- `retries`：重试次数
- `skip_existing`：跳过本地已存在文件
- `proxy`：`ProxyConfig(...)`
- `ftp_block_size`：FTP 读取块大小
- `netcdf_subset`：FTP NetCDF 裁剪配置

重要的 `NetcdfSubset` 字段：

- `bbox_lat`：纬度范围
- `bbox_lon`：经度范围
- `target_vars`：NetCDF 变量名，例如 `("tbb_07",)`
- `whole_file`：关闭裁剪，直接下载整文件
- `compression_level`：输出 NetCDF 压缩等级
- `fallback_full_download`：裁剪失败时回退到整文件下载

详细文档：

- [English tutorial](docs/TUTORIAL.md)
- [简体中文教程](docs/TUTORIAL.zh-CN.md)

教程中还包括：

- 产品能力矩阵表
- 按任务分类的 cookbook
- FAQ 与常见报错说明

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

更多 CLI 与任务示例请见：

- [简体中文教程](docs/TUTORIAL.zh-CN.md)

## 测试

```bash
python -m pytest -q
```

## 构建

```bash
python -m build
python -m twine check dist/*
```

## 发布

GitHub 仓库：

- `https://github.com/P-Coke/himawari-downloader`

PyPI 发布通过 GitHub Actions Trusted Publishing 自动完成。

发布步骤：

1. 将变更推送到 `main`
2. 创建并推送版本标签，例如 `v0.1.0`
3. GitHub Actions 会自动构建并发布到 PyPI

## 致谢与引用说明

本项目在设计上参考了
[`ghiggi/himawari_api`](https://github.com/ghiggi/himawari_api)，尤其是
Himawari 文件发现流程，以及 `latest`、`closest`、`previous`、`next`
这类查询语义的设计思路。

`himawari_api` 采用 MIT License。本项目是独立实现，没有直接 vendor
或复制该项目源码。
