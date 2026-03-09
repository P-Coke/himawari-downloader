from __future__ import annotations

import datetime as dt

from himawari_downloader.backends.ftp import FTPBackend
from himawari_downloader.backends.s3 import S3Backend
from himawari_downloader.download.runner import download_many
from himawari_downloader.errors import ConfigurationError
from himawari_downloader.models import DownloadParams, DownloadResult, QueryParams, RemoteFile


class HimawariDownloader:
    def __init__(
        self,
        *,
        ftp_host: str = "ftp.ptree.jaxa.jp",
        ftp_root: str = "/jma",
        ftp_user: str | None = None,
        ftp_password: str | None = None,
        s3_fs_args: dict | None = None,
    ) -> None:
        self._backends = {
            "ftp": FTPBackend(
                ftp_host=ftp_host,
                ftp_root=ftp_root,
                ftp_user=ftp_user,
                ftp_password=ftp_password,
            ),
            "s3": S3Backend(fs_args=s3_fs_args),
        }

    def find_files(self, query: QueryParams) -> list[RemoteFile]:
        return self._backend(query.source).find_files(query)

    def download_files(self, files: list[RemoteFile], params: DownloadParams) -> DownloadResult:
        if not files:
            return DownloadResult((), (), (), ())
        sources = {item.source for item in files}
        if len(sources) != 1:
            raise ConfigurationError("download_files accepts files from a single source only.")
        return download_many(self._backend(next(iter(sources))), files, params)

    def download(self, query: QueryParams, params: DownloadParams) -> DownloadResult:
        return self.download_files(self.find_files(query), params)

    def find_latest(self, query: QueryParams) -> list[RemoteFile]:
        return self._backend(query.source).find_latest(query)

    def find_closest(self, query: QueryParams) -> list[RemoteFile]:
        return self._backend(query.source).find_closest(query)

    def find_previous(self, query: QueryParams) -> dict[dt.datetime, list[RemoteFile]]:
        return self._backend(query.source).find_previous(query)

    def find_next(self, query: QueryParams) -> dict[dt.datetime, list[RemoteFile]]:
        return self._backend(query.source).find_next(query)

    def _backend(self, source: str):
        try:
            return self._backends[source.lower()]
        except KeyError as exc:
            raise ConfigurationError(f"Unsupported source: {source}") from exc
