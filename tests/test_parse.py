import datetime as dt

from himawari_downloader.products.parse import parse_remote_file


def test_parse_ftp_hsd_target_scene():
    item = parse_remote_file(
        "ftp",
        "/jma/hsd/202503/19/00/HS_H09_20250319_0010_B07_R302_R20_S0101.DAT.bz2",
    )
    assert item.source == "ftp"
    assert item.product == "Rad"
    assert item.scene_abbr == "R3"
    assert item.band == "B07"


def test_parse_s3_l2_cloud_mask():
    item = parse_remote_file(
        "s3",
        "s3://noaa-himawari9/AHI-L2-FLDK-Clouds/2026/01/15/0000/AHI-CMSK_v1r1_h09_s202601150000204_e202601150009398_c202601150014360.nc",
    )
    assert item.product_level == "L2"
    assert item.product == "CMSK"
    assert item.start_time == dt.datetime(2026, 1, 15, 0, 0, 20)
