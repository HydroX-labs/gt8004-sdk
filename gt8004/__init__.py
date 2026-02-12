"""GT8004 Python SDK for request analytics and observability."""

from .logger import GT8004Logger
from .types import RequestLogEntry, LogBatch
from .transport import BatchTransport

__version__ = "0.1.0"
__all__ = ["GT8004Logger", "RequestLogEntry", "LogBatch", "BatchTransport"]
