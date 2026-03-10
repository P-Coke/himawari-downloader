# 教程

[English](TUTORIAL.md) | [简体中文](TUTORIAL.zh-CN.md)

本文档解释 `himawari-downloader` 中的波段映射、主要参数配置、能力边界以及常见任务示例。

## 目录

- 两类名称的区别
- 波段映射
- 何时使用 FTP 或 S3
- 产品能力矩阵表
- `QueryParams`
- `DownloadParams`
- `NetcdfSubset`
- `ProxyConfig`
- 推荐起步组合
- cookbook
- FAQ 与常见报错

## 1. 两类名称的区别

请区分以下两类名称：

- 波段名，例如 `B07`、`B14`
- NetCDF 变量名，例如 `tbb_07`、`tbb_14`

波段名用于选择 HSD 或 S3 的 L1 通道。
NetCDF 变量名用于 FTP NetCDF 文件裁剪。

## 2. 波段映射

本包推荐的约定：

- 在 `bands` 中始终使用 `Bxx`
- 如果你从其他工具中看到 `Cxx`，请先映射为对应的 `Bxx`

示例：

- `C07` -> `B07`
- `C14` -> `B14`

常见 NetCDF 变量映射：

- `B07` -> `tbb_07`
- `B14` -> `tbb_14`

示例：

```python
bands=("B07",)
bands=("B07", "B14")
target_vars=("tbb_07",)
target_vars=("tbb_07", "tbb_14")
```

## 3. 何时使用 FTP 或 S3

以下情况推荐 `source="ftp"`：

- 你需要下载 FTP HSD
- 你需要下载 FTP NetCDF
- 你需要 FTP NetCDF 的远程 bbox / 变量裁剪

以下情况推荐 `source="s3"`：

- 你需要使用 NOAA 公共 S3 查询或下载原始文件
- 你需要 `latest`、`closest`、`previous`、`next`

## 4. 产品能力矩阵表

这是查看当前支持范围最快的方式。

| 数据源 | 产品族 | 查询模式 | 下载 | 远程裁剪 | 说明 |
| --- | --- | --- | --- | --- | --- |
| FTP | L1B HSD | `links`, `timestamps`, `dates`, `range` | 支持 | 不支持 | 支持 `bands`、分段和观测编号规则 |
| FTP | NetCDF | `links`, `timestamps`, `dates`, `range` | 支持 | 支持 | 远程 bbox 和变量裁剪仅 FTP 可用 |
| S3 | L1 通道 | `latest`, `closest`, `previous`, `next` | 支持 | 不支持 | 仅原始文件下载 |
| S3 | `CMSK` 等 L2 产品 | `latest`, `closest`, `previous`, `next` | 支持 | 不支持 | 仅原始 NetCDF 下载 |

当前常用示例：

- FTP HSD：`product_level="L1B"`、`product="Rad"`、`data_format="hsd"`
- FTP NetCDF：`product_level="L2"`、`product="NetCDF"`、`data_format="netcdf"`
- S3 云掩膜：`product_level="L2"`、`product="CMSK"`

当前不支持：

- S3 远程 NetCDF bbox 裁剪
- FTP 的 `latest`、`closest`、`previous`、`next`
- scene 生成、satpy 预处理、图像渲染

## 5. QueryParams

核心必填字段：

- `source`
- `satellite`
- `product_level`
- `product`
- `sector`

按模式使用的字段：

- `mode="links"` -> 使用 `remote_files`
- `mode="timestamps"` -> 使用 `timestamps`
- `mode="dates"` -> 使用 `dates`
- `mode="range"` -> 使用 `date_start` 和 `date_end`
- `mode="closest"` -> 使用 `target_time`
- `mode="previous"` 或 `mode="next"` -> 使用 `target_time`，可选 `count`

其他常用字段：

- `data_format`：仅 FTP，支持 `hsd` 或 `netcdf`
- `bands`：`Bxx` 元组
- `scene_abbr`：可选场景过滤，例如 `("R1",)`
- `utc_hours`：小时范围字符串，如 `"00-08"`
- `minute_step`：如果你要显式指定时间步长，可设置它
- `include_start_time`：用于 `previous` 和 `next`
- `check_consistency`：用于 `previous` 和 `next`

FTP HSD 示例：

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

S3 L2 示例：

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

主要字段：

- `out_dir`
- `max_workers`
- `retries`
- `retry_wait_sec`
- `skip_existing`
- `proxy`
- `ftp_block_size`
- `netcdf_subset`

示例：

```python
params = DownloadParams(
    out_dir="data/out",
    max_workers=4,
    retries=2,
)
```

## 7. NetcdfSubset

`NetcdfSubset` 仅用于：

- `source="ftp"`
- `data_format="netcdf"`

主要字段：

- `bbox_lat`
- `bbox_lon`
- `target_vars`
- `whole_file`
- `compression_level`
- `fallback_full_download`

示例：

```python
subset = NetcdfSubset(
    bbox_lat=(40.75, 34.44),
    bbox_lon=(110.27, 114.59),
    target_vars=("tbb_07",),
)
```

## 8. ProxyConfig

统一代理：

```python
proxy = ProxyConfig(url="http://127.0.0.1:7890")
```

按数据源分别覆盖：

```python
proxy = ProxyConfig(
    url="http://127.0.0.1:7890",
    source_overrides={
        "s3": "http://127.0.0.1:7890",
        "ftp": "http://127.0.0.1:7890",
    },
)
```

说明：

- `s3` 通过 HTTP 代理通常比较稳定
- `ftp` 直连下载已验证可用
- `ftp` 通过部分 HTTP 代理进行远程 NetCDF 读取时，可能超时或失败
- 如果你优先追求 FTP NetCDF 稳定性，建议优先直连

## 9. 推荐起步组合

FTP HSD 单波段：

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

FTP NetCDF 裁剪：

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

S3 最新 L2 查询：

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

本节按任务组织，而不是按 API 对象组织。

### 下载一天的 FTP HSD 单波段

适用于从 JAXA FTP 下载标准 L1B 通道。

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

### 下载多个 FTP HSD 波段

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

### 下载指定 FTP NetCDF 文件并进行裁剪

注意 `target_vars` 应使用 NetCDF 变量名，而不是 `Bxx`。

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

### 下载完整 FTP NetCDF 文件，不做裁剪

```python
params = DownloadParams(
    out_dir="data/ftp_full",
    netcdf_subset=NetcdfSubset(whole_file=True),
)
```

### 查询最新的 S3 云掩膜并下载

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

### 查找最接近目标时刻的 S3 文件

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

### 获取目标时刻之前或之后的 S3 文件

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

如果要向后找，把 `mode="previous"` 改为 `mode="next"`。

### 为 S3 和 FTP 共享一个代理

```python
from himawari_downloader import DownloadParams, ProxyConfig

params = DownloadParams(
    out_dir="data/out",
    proxy=ProxyConfig(url="http://127.0.0.1:7890"),
)
```

### 为 S3 和 FTP 分别设置不同代理

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

### CLI 示例：先查询 FTP 文件

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

### CLI 示例：下载最新的 S3 云掩膜

```bash
himawari-download latest \
  --source s3 \
  --satellite HIMAWARI-9 \
  --product-level L2 \
  --product CMSK \
  --sector FLDK
```

## 11. FAQ 与常见报错

### `bands` 和 `target_vars` 有什么区别？

- `bands` 用于波段选择，例如 `("B07", "B14")`
- `target_vars` 用于 NetCDF 变量名，例如 `("tbb_07", "tbb_14")`
- 如果你在裁剪 FTP NetCDF 文件，应使用 `target_vars`

### 现在可以下载 S3 云掩膜吗？

可以。使用 `source="s3"`、`product_level="L2"`、`product="CMSK"` 即可查询并下载原始文件。

### 为什么 FTP NetCDF 裁剪在 HTTP 代理后面失败？

常见原因：

- 代理对普通 HTTP 流量支持良好，但对 FTP 读取不稳定
- 远程 NetCDF 访问会产生多次读取，容易在代理链路上超时
- 代理可能不支持当前 FTP 客户端实际使用的传输模式

建议：

- 优先尝试 FTP 直连
- 降低并发数
- 提高重试次数
- 如果后续加入本地回退路径，优先考虑先整文件下载再本地裁剪

### 为什么我会收到 NetCDF 裁剪相关的依赖错误？

FTP NetCDF 裁剪需要安装 `ftp-netcdf` extra。

```bash
pip install "himawari-downloader[ftp-netcdf]"
```

或安装完整功能：

```bash
pip install "himawari-downloader[all]"
```

### 为什么我会收到 S3 相关的依赖错误？

S3 backend 需要安装 `s3` extra。

```bash
pip install "himawari-downloader[s3]"
```

### 卫星名称应该怎么写？

当前推荐：

- FTP：`H08`、`H09`
- S3：`HIMAWARI-8`、`HIMAWARI-9`

如果你在 FTP 和 S3 间切换，不要假设两边使用完全相同的卫星名称格式。

### 为什么 `latest` 不能用于 FTP？

当前 `latest`、`closest`、`previous`、`next` 只实现于 `s3` 查询流程。
FTP 目前使用 `links`、`timestamps`、`dates`、`range`。

### 为什么 bbox 裁剪后没有数据，或者文件特别小？

常见原因：

- 纬度范围和你的目标区域方向不一致
- 经度范围没有覆盖源文件区域
- `target_vars` 中的变量名在源 NetCDF 中不存在
- 所选区域本身很小

请检查：

- bbox 数值
- 文件时间和区域类型
- `target_vars` 中的变量名

### 哪些产品适合作为第一批测试？

推荐从以下简单组合开始：

- FTP HSD：`L1B` + `Rad` + `B07`
- FTP NetCDF 裁剪：`NetCDF` + `tbb_07`
- S3 L2：`CMSK`
