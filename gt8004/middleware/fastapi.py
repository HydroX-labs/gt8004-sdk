"""FastAPI middleware for GT8004 request logging."""

import time
import uuid
from typing import TYPE_CHECKING
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

if TYPE_CHECKING:
    from ..logger import GT8004Logger

from ..types import RequestLogEntry


class GT8004Middleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that automatically logs requests to GT8004.

    Usage:
        from fastapi import FastAPI
        from gt8004 import GT8004Logger
        from gt8004.middleware.fastapi import GT8004Middleware

        logger = GT8004Logger(agent_id="...", api_key="...")
        logger.transport.start_auto_flush()

        app = FastAPI()
        app.add_middleware(GT8004Middleware, logger=logger)
    """

    def __init__(self, app, logger: "GT8004Logger"):
        """
        Initialize the middleware.

        Args:
            app: FastAPI application
            logger: GT8004Logger instance
        """
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        """
        Process each request and log it to GT8004.

        Args:
            request: Incoming FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response from the route handler
        """
        # Start timing
        start_time = time.time()
        request_id = str(uuid.uuid4())

        # Capture request body (optional, limited size)
        request_body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if len(body_bytes) <= 16384:  # 16KB limit
                    request_body = body_bytes.decode('utf-8', errors='ignore')
            except Exception:
                pass

        # Process request
        response = await call_next(request)

        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # ms

        # Create log entry
        entry = RequestLogEntry(
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            response_ms=response_time,
            request_body=request_body,
            headers={
                "user-agent": request.headers.get("user-agent"),
                "content-type": request.headers.get("content-type"),
                "referer": request.headers.get("referer"),
            },
            ip_address=request.client.host if request.client else None,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

        # Log asynchronously
        await self.logger.log(entry)

        return response
