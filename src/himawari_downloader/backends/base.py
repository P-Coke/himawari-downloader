from __future__ import annotations

import abc
import datetime as dt
from pathlib import Path

from himawari_downloader.models import DownloadParams, QueryParams, RemoteFile


class BaseBackend(abc.ABC):
    source: str

    @abc.abstractmethod
    def find_files(self, query: QueryParams) -> list[RemoteFile]:
        raise NotImplementedError

    def find_latest(self, query: QueryParams) -> list[RemoteFile]:
        raise NotImplementedError

    def find_closest(self, query: QueryParams) -> list[RemoteFile]:
        raise NotImplementedError

    def find_previous(self, query: QueryParams) -> dict[dt.datetime, list[RemoteFile]]:
        raise NotImplementedError

    def find_next(self, query: QueryParams) -> dict[dt.datetime, list[RemoteFile]]:
        raise NotImplementedError

    @abc.abstractmethod
    def download_file(self, remote_file: RemoteFile, params: DownloadParams) -> Path:
        raise NotImplementedError
