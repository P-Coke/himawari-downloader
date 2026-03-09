from __future__ import annotations

import contextlib
import os
import socket
from urllib.parse import urlparse

import socks

from himawari_downloader.errors import ProxyConfigurationError
from himawari_downloader.models import ProxyConfig


def resolve_proxy(proxy: ProxyConfig | None, source: str) -> str | None:
    if proxy is not None:
        return proxy.resolve_for_source(source)
    if source == "s3":
        return os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("ALL_PROXY")
    return os.getenv("ALL_PROXY") or os.getenv("FTP_PROXY")


def build_s3_fs_args(proxy: ProxyConfig | None) -> dict:
    proxy_url = resolve_proxy(proxy, "s3")
    args = {"anon": True}
    if proxy_url:
        args["config_kwargs"] = {"proxies": {"http": proxy_url, "https": proxy_url}}
    return args


@contextlib.contextmanager
def ftp_proxy_context(proxy: ProxyConfig | None):
    proxy_url = resolve_proxy(proxy, "ftp")
    if not proxy_url:
        yield
        return
    parsed = urlparse(proxy_url)
    scheme = parsed.scheme.lower()
    if scheme not in {"socks5", "socks5h", "socks4", "socks4a", "http", "https"}:
        raise ProxyConfigurationError("FTP backend supports SOCKS or HTTP proxy URLs only.")
    if parsed.hostname is None or parsed.port is None:
        raise ProxyConfigurationError("Proxy URL must include host and port.")
    proxy_type = {
        "socks5": socks.PROXY_TYPE_SOCKS5,
        "socks5h": socks.PROXY_TYPE_SOCKS5,
        "socks4": socks.PROXY_TYPE_SOCKS4,
        "socks4a": socks.PROXY_TYPE_SOCKS4,
        "http": socks.PROXY_TYPE_HTTP,
        "https": socks.PROXY_TYPE_HTTP,
    }[scheme]
    original_socket = socket.socket
    socks.set_default_proxy(
        proxy_type,
        parsed.hostname,
        parsed.port,
        username=parsed.username,
        password=parsed.password,
    )
    socket.socket = socks.socksocket
    try:
        yield
    finally:
        socket.socket = original_socket
        socks.set_default_proxy()
