import pytest

from himawari_downloader.backends.ftp import FTPBackend
from himawari_downloader.errors import ConfigurationError, UnsupportedOperationError
from himawari_downloader.models import DownloadParams, NetcdfSubset, QueryParams


def test_ftp_dates_skip_housekeeping():
    backend = FTPBackend()
    files = backend.find_files(
        QueryParams(
            source="ftp",
            satellite="H09",
            product_level="L1B",
            product="Rad",
            sector="FLDK",
            mode="dates",
            data_format="hsd",
            dates=("2025-03-19",),
            utc_hours="02",
            bands=("B07",),
        )
    )
    hhmm = {item.start_time.strftime("%H%M") for item in files}
    assert "0240" not in hhmm
    assert "0250" not in hhmm


def test_ftp_previous_is_unsupported():
    backend = FTPBackend()
    with pytest.raises(UnsupportedOperationError):
        backend.find_previous(
            QueryParams(
                source="ftp",
                satellite="H09",
                product_level="L1B",
                product="Rad",
                sector="FLDK",
                mode="previous",
                data_format="hsd",
                target_time="2025-03-19 00:10:00",
            )
        )


def test_ftp_netcdf_subset_requires_bbox(tmp_path):
    backend = FTPBackend()
    remote = backend.find_files(
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
    )[0]
    with pytest.raises(ConfigurationError):
        backend.download_file(
            remote,
            DownloadParams(out_dir=tmp_path, netcdf_subset=NetcdfSubset()),
        )


def test_ftp_japan_bbox_validation():
    backend = FTPBackend()
    with pytest.raises(ConfigurationError):
        backend._validate_japan_bbox(  # noqa: SLF001
            "/jma/netcdf/202503/19/NC_H09_20250319_0010_r14_FLDK.02701_02601.nc",
            (10.0, 20.0),
            (100.0, 110.0),
        )
