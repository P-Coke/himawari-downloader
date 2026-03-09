from himawari_downloader.cli import build_parser


def test_cli_parse_download_with_proxy_and_subset():
    parser = build_parser()
    args = parser.parse_args(
        [
            "download",
            "--source", "ftp",
            "--satellite", "H09",
            "--product-level", "L2",
            "--product", "NetCDF",
            "--sector", "FLDK",
            "--data-format", "netcdf",
            "--date-start", "2025-03-19",
            "--date-end", "2025-03-19",
            "--proxy", "socks5://127.0.0.1:1080",
            "--bbox-lat", "40.75,34.44",
            "--bbox-lon", "110.27,114.59",
        ]
    )
    assert args.command == "download"
    assert args.proxy == "socks5://127.0.0.1:1080"
    assert args.bbox_lat == "40.75,34.44"
