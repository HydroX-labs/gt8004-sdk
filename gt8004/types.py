"""Type definitions for GT8004 SDK."""

from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class RequestLogEntry(BaseModel):
    """A single request log entry to be sent to GT8004 analytics."""

    request_id: str
    method: str
    path: str
    status_code: int
    response_ms: float

    # Optional analytics fields
    customer_id: Optional[str] = None
    tool_name: Optional[str] = None
    error_type: Optional[str] = None

    # X-402 payment protocol fields
    x402_amount: Optional[float] = None
    x402_tx_hash: Optional[str] = None
    x402_token: Optional[str] = None
    x402_payer: Optional[str] = None

    # Request/response body (limited size)
    request_body: Optional[str] = None
    response_body: Optional[str] = None
    request_body_size: Optional[int] = None
    response_body_size: Optional[int] = None

    # Request metadata
    headers: Optional[Dict[str, str]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referer: Optional[str] = None
    content_type: Optional[str] = None
    accept_language: Optional[str] = None
    protocol: Optional[str] = None

    # Source identifier
    source: str = "sdk"

    # Timestamp (ISO 8601 format with 'Z' suffix)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class LogBatch(BaseModel):
    """A batch of log entries to send to the ingest API."""

    agent_id: str
    sdk_version: str = "python-0.1.0"
    entries: List[RequestLogEntry]
