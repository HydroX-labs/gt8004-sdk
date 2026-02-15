"""Tests for FastAPI/ASGI middleware."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gt8004.middleware.fastapi import GT8004Middleware
from gt8004.types import RequestLogEntry


def _make_logger(protocol=None):
    """Create a mock GT8004Logger with async log method."""
    logger = MagicMock()
    logger.protocol = protocol
    logger.log = AsyncMock()
    return logger


def _make_app(logger):
    """Create a FastAPI app with GT8004 middleware."""
    app = FastAPI()
    app.add_middleware(GT8004Middleware, logger=logger)

    @app.get("/api/search")
    async def search():
        return {"results": []}

    @app.post("/a2a/tasks")
    async def tasks(body: dict = None):
        return {"status": "ok"}

    @app.get("/health")
    async def health():
        return {"ok": True}

    return app


class TestFastAPIMiddlewareBasic:
    def test_passes_through_request(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_logs_get_request(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        client.get("/api/search")

        logger.log.assert_called_once()
        entry = logger.log.call_args[0][0]
        assert isinstance(entry, RequestLogEntry)
        assert entry.method == "GET"
        assert entry.path == "/api/search"
        assert entry.status_code == 200
        assert entry.response_ms > 0

    def test_logs_post_request(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        client.post("/a2a/tasks", json={"skill_id": "translate"})

        logger.log.assert_called_once()
        entry = logger.log.call_args[0][0]
        assert entry.method == "POST"
        assert entry.path == "/a2a/tasks"
        assert entry.request_body is not None


class TestFastAPIMiddlewareProtocol:
    def test_a2a_extracts_skill_id(self):
        logger = _make_logger(protocol="a2a")
        app = _make_app(logger)
        client = TestClient(app)

        client.post("/a2a/tasks", json={"skill_id": "translate"})

        entry = logger.log.call_args[0][0]
        assert entry.tool_name == "translate"

    def test_http_extracts_path_segment(self):
        logger = _make_logger(protocol=None)
        app = _make_app(logger)
        client = TestClient(app)

        client.get("/api/search")

        entry = logger.log.call_args[0][0]
        assert entry.tool_name == "search"

    def test_mcp_extracts_tool_name(self):
        logger = _make_logger(protocol="mcp")
        app = FastAPI()
        app.add_middleware(GT8004Middleware, logger=logger)

        @app.post("/mcp")
        async def mcp_endpoint():
            return {"result": "ok"}

        client = TestClient(app)
        mcp_body = {"method": "tools/call", "params": {"name": "search"}}
        client.post("/mcp", json=mcp_body)

        entry = logger.log.call_args[0][0]
        assert entry.tool_name == "search"


class TestFastAPIMiddlewareMetadata:
    def test_captures_request_id(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        client.get("/health")

        entry = logger.log.call_args[0][0]
        assert entry.request_id is not None
        assert len(entry.request_id) == 36  # UUID format

    def test_captures_timestamp(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        client.get("/health")

        entry = logger.log.call_args[0][0]
        assert entry.timestamp.endswith("Z")

    def test_captures_response_body(self):
        logger = _make_logger()
        app = _make_app(logger)
        client = TestClient(app)

        client.get("/health")

        entry = logger.log.call_args[0][0]
        assert entry.response_body is not None
        assert "ok" in entry.response_body
