class HimawariDownloaderError(Exception):
    """Base package error."""


class ConfigurationError(HimawariDownloaderError):
    """Raised when inputs are incomplete or contradictory."""


class UnsupportedOperationError(HimawariDownloaderError):
    """Raised when a backend does not support an operation."""


class RemoteFileNotFoundError(HimawariDownloaderError):
    """Raised when a remote file does not exist."""


class IntegrityCheckError(HimawariDownloaderError):
    """Raised when a downloaded file fails integrity checks."""


class ProxyConfigurationError(HimawariDownloaderError):
    """Raised when proxy settings are invalid for a backend."""
