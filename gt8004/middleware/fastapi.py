"""FastAPI middleware for GT8004 request logging."""

import json
import time
import uuid
from typing import TYPE_CHECKING
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

if TYPE_CHECKING:
    from ..logger import GT8004Logger

from ..types import RequestLogEntry

_BODY_LIMIT = 16384  # 16 KB


def _extract_mcp_tool_name(body: str | None) -> str | None:
    """Extract tool name from MCP JSON-RPC request body."""
    if not body:
        return None
    try:
        data = json.loads(body)
        if data.get("method") == "tools/call":
            return data.get("params", {}).get("name")
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass
    return None


def _extract_a2a_tool_name(body: str | None, path: str) -> str | None:
    """Extract skill/tool name from A2A request body or path."""
    if body:
        try:
            data = json.loads(body)
            skill = data.get("skill_id")
            if skill:
                return skill
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass
    # Fallback: last path segment
    segments = path.rstrip("/").split("/")
    return segments[-1] if segments else None


def _extract_http_tool_name(path: str) -> str | None:
    """Extract tool name from HTTP path (last meaningful segment)."""
    segments = path.rstrip("/").split("/")
    return segments[-1] if segments else None


class GT8004Middleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that automatically logs requests to GT8004.

    Supports protocol-aware tool name extraction:
    - protocol="http": extracts tool name from URL path
    - protocol="mcp": extracts tool name from JSON-RPC body (tools/call)
    - protocol="a2a": extracts skill_id from request body

    Usage:
        from fastapi import FastAPI
        from gt8004 import GT8004Logger
        from gt8004.middleware.fastapi import GT8004Middleware

        # HTTP API (default)
        logger = GT8004Logger(agent_id="...", api_key="...")

        # MCP Server
        logger = GT8004Logger(agent_id="...", api_key="...", protocol="mcp")

        # A2A Server
        logger = GT8004Logger(agent_id="...", api_key="...", protocol="a2a")

        logger.transport.start_auto_flush()
        app = FastAPI()
        app.add_middleware(GT8004Middleware, logger=logger)
    """

    def __init__(self, app, logger: "GT8004Logger"):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())

        # Capture request body
        request_body = None
        request_body_size = 0
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body_bytes = await request.body()
                request_body_size = len(body_bytes)
                if request_body_size <= _BODY_LIMIT:
                    request_body = body_bytes.decode("utf-8", errors="ignore")
            except Exception:
                pass

        # Process request
        response = await call_next(request)

        # Capture response body by reading the streaming response
        response_body = None
        response_body_size = 0
        try:
            body_chunks: list[bytes] = []
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                body_chunks.append(chunk)
            raw = b"".join(body_chunks)
            response_body_size = len(raw)
            if response_body_size <= _BODY_LIMIT:
                response_body = raw.decode("utf-8", errors="ignore")
            # Re-create response with the consumed body
            response = Response(
                content=raw,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        except Exception:
            pass

        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # ms

        # Protocol-specific tool name extraction
        protocol = self.logger.protocol
        path = str(request.url.path)

        if protocol == "mcp":
            tool_name = _extract_mcp_tool_name(request_body)
        elif protocol == "a2a":
            tool_name = _extract_a2a_tool_name(request_body, path)
        else:
            tool_name = _extract_http_tool_name(path)

        # Create log entry
        raw_headers = {
            "user-agent": request.headers.get("user-agent"),
            "content-type": request.headers.get("content-type"),
            "referer": request.headers.get("referer"),
        }
        headers = {k: v for k, v in raw_headers.items() if v is not None}

        entry = RequestLogEntry(
            request_id=request_id,
            method=request.method,
            path=path,
            status_code=response.status_code,
            response_ms=response_time,
            tool_name=tool_name,
            protocol=protocol,
            request_body=request_body,
            request_body_size=request_body_size,
            response_body=response_body,
            response_body_size=response_body_size,
            headers=headers if headers else None,
            ip_address=request.client.host if request.client else None,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        # Log asynchronously
        await self.logger.log(entry)

        return response