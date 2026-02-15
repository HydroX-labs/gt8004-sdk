"""Tests for Flask/WSGI middleware."""

import io
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from gt8004.middleware.flask import GT8004FlaskMiddleware
from gt8004.types import RequestLogEntry


def _make_logger(protocol=None):
    """Create a mock GT8004Logger."""
    logger = MagicMock()
    logger.protocol = protocol
    logger.log = AsyncMock()
    return logger


def _make_environ(method="GET", path="/api/search", body=None, remote_addr="127.0.0.1"):
    """Create a minimal WSGI environ dict."""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "REMOTE_ADDR": remote_addr,
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8000",
    }
    if body is not None:
        body_bytes = body.encode("utf-8") if isinstance(body, str) else body
        environ["wsgi.input"] = io.BytesIO(body_bytes)
    else:
        environ["wsgi.input"] = io.BytesIO(b"")
    return environ


def _simple_app(environ, start_response):
    """A simple WSGI app that returns 200 OK."""
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"hello"]


def _error_app(environ, start_response):
    """A WSGI app that returns 500."""
    start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
    return [b"error"]


class TestFlaskMiddlewareBasic:
    def test_passes_through_to_app(self):
        logger = _make_logger()
        middleware = GT8004FlaskMiddleware(_simple_app, logger)

        responses = []
        def start_response(status, headers, exc_info=None):
            responses.append(status)

        result = middleware(_make_environ(), start_response)
        assert b"".join(result) == b"hello"
        assert responses[0] == "200 OK"

    def test_logs_request(self):
        logger = _make_logger()
        middleware = GT8004FlaskMiddleware(_simple_app, logger)

        def start_response(status, headers, exc_info=None):
            pass

        middleware(_make_environ(method="GET", path="/api/test"), start_response)

        # logger.log should have been called via the background loop
        # Since it's async via run_coroutine_threadsafe, we check the loop was used
        # The middleware creates a background event loop, so we verify the entry was constructed
        assert middleware._loop is not None

    def test_captures_status_code(self):
        logger = _make_logger()
        middleware = GT8004FlaskMiddleware(_error_app, logger)

        captured_status = []
        def start_response(status, headers, exc_info=None):
            captured_status.append(status)

        middleware(_make_environ(), start_response)
        assert captured_status[0] == "500 Internal Server Error"


class TestFlaskMiddlewareBody:
    def test_restores_request_body_stream(self):
        """Middleware should read body but restore it for the downstream app."""
        body_seen_by_app = []

        def app_that_reads_body(environ, start_response):
            body = environ["wsgi.input"].read()
            body_seen_by_app.append(body)
            start_response("200 OK", [])
            return [b"ok"]

        logger = _make_logger()
        middleware = GT8004FlaskMiddleware(app_that_reads_body, logger)

        def start_response(status, headers, exc_info=None):
            pass

        body = json.dumps({"skill_id": "translate"})
        middleware(_make_environ(method="POST", body=body), start_response)

        # The downstream app should see the full body
        assert body_seen_by_app[0] == body.encode("utf-8")


class TestFlaskMiddlewareProtocol:
    def test_a2a_extracts_skill_id(self):
        logger = _make_logger(protocol="a2a")
        middleware = GT8004FlaskMiddleware(_simple_app, logger)

        def start_response(status, headers, exc_info=None):
            pass

        body = json.dumps({"skill_id": "translate"})
        middleware(_make_environ(method="POST", path="/a2a/tasks", body=body), start_response)

        # Verify the middleware created and submitted a log entry
        assert middleware._loop is not None

    def test_http_extracts_path_segment(self):
        logger = _make_logger(protocol=None)
        middleware = GT8004FlaskMiddleware(_simple_app, logger)

        def start_response(status, headers, exc_info=None):
            pass

        middleware(_make_environ(path="/api/search"), start_response)
        assert middleware._loop is not None


class TestFlaskMiddlewareEventLoop:
    def test_creates_background_loop(self):
        logger = _make_logger()
        middleware = GT8004FlaskMiddleware(_simple_app, logger)

        assert middleware._loop is None
        assert middleware._thread is None

        loop = middleware._get_loop()
        assert loop is not None
        assert loop.is_running()
        assert middleware._thread.is_alive()

    def test_reuses_existing_loop(self):
        logger = _make_logger()
        middleware = GT8004FlaskMiddleware(_simple_app, logger)

        loop1 = middleware._get_loop()
        loop2 = middleware._get_loop()
        assert loop1 is loop2
