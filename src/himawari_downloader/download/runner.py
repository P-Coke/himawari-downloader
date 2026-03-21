from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from himawari_downloader.backends.base import BaseBackend
from himawari_downloader.errors import RemoteFileNotFoundError
from himawari_downloader.models import DownloadEvent, DownloadParams, DownloadResult, RemoteFile


def download_many(
    backend: BaseBackend,
    files: list[RemoteFile],
    params: DownloadParams,
) -> DownloadResult:
    saved: list[Path] = []
    skipped: list[Path] = []
    missing: list[str] = []
    failed: list[str] = []
    processed = 0
    total = len(files)

    out_dir = Path(params.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    def _work(item: RemoteFile):
        path = backend.download_file(item, params)
        return item, path

    if params.max_workers <= 1 or len(files) <= 1:
        for item in files:
            out_path = out_dir / item.remote_path.replace("\\", "/").split("/")[-1]
            if params.skip_existing and out_path.exists():
                skipped.append(out_path)
                processed += 1
                _emit_progress(params, DownloadEvent("skipped", item.remote_path, processed, total, saved_path=out_path))
                continue
            try:
                _emit_progress(params, DownloadEvent("running", item.remote_path, processed, total))
                _, saved_path = _run_with_retries(_work, item, params)
                saved.append(saved_path)
                processed += 1
                _emit_progress(params, DownloadEvent("saved", item.remote_path, processed, total, saved_path=saved_path))
            except RemoteFileNotFoundError:
                missing.append(item.remote_path)
                processed += 1
                _emit_progress(params, DownloadEvent("missing", item.remote_path, processed, total))
            except Exception as exc:
                failed.append(f"{item.remote_path} | {exc}")
                processed += 1
                _emit_progress(params, DownloadEvent("failed", item.remote_path, processed, total, error=str(exc)))
    else:
        futures = {}
        with ThreadPoolExecutor(max_workers=params.max_workers) as executor:
            for item in files:
                out_path = out_dir / item.remote_path.replace("\\", "/").split("/")[-1]
                if params.skip_existing and out_path.exists():
                    skipped.append(out_path)
                    processed += 1
                    _emit_progress(params, DownloadEvent("skipped", item.remote_path, processed, total, saved_path=out_path))
                    continue
                _emit_progress(params, DownloadEvent("running", item.remote_path, processed, total))
                futures[executor.submit(_run_with_retries, _work, item, params)] = item
            for future in as_completed(futures):
                item = futures[future]
                try:
                    _, saved_path = future.result()
                    saved.append(saved_path)
                    processed += 1
                    _emit_progress(params, DownloadEvent("saved", item.remote_path, processed, total, saved_path=saved_path))
                except RemoteFileNotFoundError:
                    missing.append(item.remote_path)
                    processed += 1
                    _emit_progress(params, DownloadEvent("missing", item.remote_path, processed, total))
                except Exception as exc:
                    failed.append(f"{item.remote_path} | {exc}")
                    processed += 1
                    _emit_progress(params, DownloadEvent("failed", item.remote_path, processed, total, error=str(exc)))

    return DownloadResult(
        saved_paths=tuple(saved),
        skipped_paths=tuple(skipped),
        missing_files=tuple(missing),
        failed_files=tuple(failed),
    )


def _run_with_retries(fn, item: RemoteFile, params: DownloadParams):
    last_error: Exception | None = None
    for attempt in range(1, params.retries + 2):
        try:
            return fn(item)
        except RemoteFileNotFoundError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt > params.retries:
                break
            time.sleep(params.retry_wait_sec)
    assert last_error is not None
    raise last_error


def _emit_progress(params: DownloadParams, event: DownloadEvent) -> None:
    if params.progress_callback is not None:
        params.progress_callback(event)
