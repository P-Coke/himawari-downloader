import pytest

from himawari_downloader import DownloadParams, HimawariDownloader, QueryParams
from himawari_downloader.errors import ConfigurationError


def test_download_files_requires_single_source(tmp_path):
    downloader = HimawariDownloader()
    files = [
        downloader.find_files(
            QueryParams(
                source="ftp",
                satellite="H09",
                product_level="L2",
                product="NetCDF",
                sector="FLDK",
                mode="links",
                data_format="netcdf",
                remote_files=("/jma/netcdf/202503/19/NC_H09_20250319_0010_R21_FLDK.07001_06001.nc",),
            )
        )[0],
        downloader.find_files(
            QueryParams(
                source="s3",
                satellite="HIMAWARI-9",
                product_level="L2",
                product="CMSK",
                sector="FLDK",
                mode="links",
                remote_files=("s3://noaa-himawari9/AHI-L2-FLDK-Clouds/2026/01/15/0000/AHI-CMSK_v1r1_h09_s202601150000204_e202601150009398_c202601150014360.nc",),
            )
        )[0],
    ]
    with pytest.raises(ConfigurationError):
        downloader.download_files(files, DownloadParams(out_dir=tmp_path))
