import datetime as dt

import pytest

from himawari_downloader.backends.s3 import S3Backend
from himawari_downloader.errors import ConfigurationError
from himawari_downloader.models import QueryParams, RemoteFile


class FakeS3FS:
    def __init__(self, mapping):
        self.mapping = mapping

    def glob(self, pattern):
        return self.mapping.get(pattern, [])


def test_s3_find_files_filters_and_dedupes(monkeypatch):
    backend = S3Backend()
    mapping = {
        "s3://noaa-himawari9/AHI-L1b-FLDK/2026/01/15/0000/*": [
            "noaa-himawari9/AHI-L1b-FLDK/2026/01/15/0000/HS_H09_20260115_0000_B07_FLDK_R10_S0110.DAT.bz2",
            "noaa-himawari9/AHI-L1b-FLDK/2026/01/15/0000/HS_H09_20260115_0000_B07_FLDK_R20_S0110.DAT.bz2",
            "noaa-himawari9/AHI-L1b-FLDK/2026/01/15/0000/HS_H09_20260115_0000_B14_FLDK_R20_S0110.DAT.bz2",
        ]
    }
    monkeypatch.setattr(backend, "_get_fs", lambda params=None: FakeS3FS(mapping))
    files = backend.find_files(
        QueryParams(
            source="s3",
            satellite="HIMAWARI-9",
            product_level="L1B",
            product="Rad",
            sector="FLDK",
            mode="timestamps",
            timestamps=("2026-01-15 00:00:00",),
            bands=("B07", "B14"),
        )
    )
    assert len(files) == 2
    assert {item.band for item in files} == {"B07", "B14"}


def test_s3_find_closest_requires_target_time():
    backend = S3Backend()
    with pytest.raises(ConfigurationError):
        backend.find_closest(
            QueryParams(
                source="s3",
                satellite="HIMAWARI-9",
                product_level="L2",
                product="CMSK",
                sector="FLDK",
                mode="closest",
            )
        )


def test_s3_previous_grouping(monkeypatch):
    backend = S3Backend()
    first = RemoteFile(
        source="s3",
        remote_path="s3://x/0000/AHI-CMSK_v1r1_h09_s202601150000204_e202601150009398_c202601150014360.nc",
        satellite="HIMAWARI-9",
        product_level="L2",
        product="CMSK",
        sector="FLDK",
        start_time=dt.datetime(2026, 1, 15, 0, 0, 20),
        end_time=dt.datetime(2026, 1, 15, 0, 9, 39),
        format="netcdf",
    )
    second = RemoteFile(
        source="s3",
        remote_path="s3://x/0010/AHI-CMSK_v1r1_h09_s202601150010204_e202601150019398_c202601150024360.nc",
        satellite="HIMAWARI-9",
        product_level="L2",
        product="CMSK",
        sector="FLDK",
        start_time=dt.datetime(2026, 1, 15, 0, 10, 20),
        end_time=dt.datetime(2026, 1, 15, 0, 19, 39),
        format="netcdf",
    )
    monkeypatch.setattr(backend, "_find_time_window_files", lambda query: [first, second])
    grouped = backend.find_previous(
        QueryParams(
            source="s3",
            satellite="HIMAWARI-9",
            product_level="L2",
            product="CMSK",
            sector="FLDK",
            mode="previous",
            target_time="2026-01-15 00:10:20",
            count=1,
        )
    )
    assert list(grouped) == [dt.datetime(2026, 1, 15, 0, 0, 20)]
