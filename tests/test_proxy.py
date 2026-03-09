import pytest

from himawari_downloader.errors import ProxyConfigurationError
from himawari_downloader.models import ProxyConfig
from himawari_downloader.transport import build_s3_fs_args, ftp_proxy_context, resolve_proxy


def test_resolve_proxy_with_override():
    proxy = ProxyConfig(
        url="http://common:8080",
        source_overrides={"ftp": "socks5://127.0.0.1:1080"},
    )
    assert resolve_proxy(proxy, "ftp") == "socks5://127.0.0.1:1080"
    assert resolve_proxy(proxy, "s3") == "http://common:8080"


def test_build_s3_fs_args_with_proxy():
    proxy = ProxyConfig(url="http://proxy:8080")
    fs_args = build_s3_fs_args(proxy)
    assert fs_args["config_kwargs"]["proxies"]["https"] == "http://proxy:8080"


def test_ftp_proxy_accepts_http():
    proxy = ProxyConfig(url="http://proxy:8080")
    with ftp_proxy_context(proxy):
        pass


def test_ftp_proxy_rejects_unknown_scheme():
    proxy = ProxyConfig(url="ssh://proxy:8080")
    with pytest.raises(ProxyConfigurationError):
        with ftp_proxy_context(proxy):
            pass
