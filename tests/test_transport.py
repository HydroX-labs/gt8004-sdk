"""Tests for BatchTransport."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import httpx

from gt8004.transport import BatchTransport
from gt8004.types import RequestLogEntry


def _make_entry(request_id="r1"):
    return RequestLogEntry(
        request_id=request_id, method="GET", path="/test",
        status_code=200, response_ms=5.0,
    )


def _ok_response():
    """Create a mock response that behaves like httpx.Response(200)."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()  # no-op for success
    return resp


class TestBatchTransportInit:
    def test_defaults(self):
        t = BatchTransport(
            ingest_url="http://localhost/v1/ingest",
            api_key="key", agent_id="agent",
        )
        assert t.batch_size == 50
        assert t.flush_interval == 5.0
        assert t.buffer == []
        assert t.consecutive_failures == 0

    def test_custom_settings(self):
        t = BatchTransport(
            ingest_url="http://x/ingest",
            api_key="k", agent_id="a",
            batch_size=10, flush_interval=1.0,
        )
        assert t.batch_size == 10
        assert t.flush_interval == 1.0


class TestBatchTransportAdd:
    @pytest.mark.asyncio
    async def test_add_to_buffer(self):
        t = BatchTransport(
            ingest_url="http://x/ingest", api_key="k", agent_id="a",
            batch_size=100,
        )
        entry = _make_entry()
        await t.add(entry)
        assert len(t.buffer) == 1
        assert t.buffer[0] is entry

    @pytest.mark.asyncio
    async def test_auto_flush_at_batch_size(self):
        t = BatchTransport(
            ingest_url="http://x/ingest", api_key="k", agent_id="a",
            batch_size=2,
        )
        # Mock the HTTP call to prevent actual network requests
        t.client = AsyncMock()
        t.client.post = AsyncMock(return_value=_ok_response())

        await t.add(_make_entry("r1"))
        assert len(t.buffer) == 1  # not yet at batch size

        await t.add(_make_entry("r2"))
        # After reaching batch_size, buffer should be flushed
        assert len(t.buffer) == 0
        t.client.post.assert_called_once()


class TestBatchTransportFlush:
    @pytest.mark.asyncio
    async def test_flush_sends_batch(self):
        t = BatchTransport(
            ingest_url="http://x/ingest", api_key="k", agent_id="a",
        )
        t.client = AsyncMock()
        t.client.post = AsyncMock(return_value=_ok_response())

        await t.add(_make_entry())
        await t.flush()

        assert len(t.buffer) == 0
        t.client.post.assert_called_once()

        # Verify auth header
        call_kwargs = t.client.post.call_args
        assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer k"

    @pytest.mark.asyncio
    async def test_flush_empty_buffer_is_noop(self):
        t = BatchTransport(
            ingest_url="http://x/ingest", api_key="k", agent_id="a",
        )
        t.client = AsyncMock()
        t.client.post = AsyncMock()

        await t.flush()
        t.client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_circuit_breaker_skips_flush(self):
        t = BatchTransport(
            ingest_url="http://x/ingest", api_key="k", agent_id="a",
        )
        t.client = AsyncMock()
        t.client.post = AsyncMock()

        # Set circuit breaker to future time
        t.circuit_breaker_until = time.time() + 60
        await t.add(_make_entry())
        await t.flush()

        # Should not have sent because circuit breaker is active
        t.client.post.assert_not_called()
        # Entry stays in buffer
        assert len(t.buffer) == 1


class TestBatchTransportRetry:
    @pytest.mark.asyncio
    async def test_requeues_on_failure(self):
        t = BatchTransport(
            ingest_url="http://x/ingest", api_key="k", agent_id="a",
        )
        t.client = AsyncMock()
        t.client.post = AsyncMock(side_effect=httpx.HTTPError("fail"))

        await t.add(_make_entry("r1"))
        await t.flush()

        # After 3 retries fail, entries should be re-queued
        assert len(t.buffer) == 1
        assert t.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_activates_after_5_failures(self):
        t = BatchTransport(
            ingest_url="http://x/ingest", api_key="k", agent_id="a",
        )
        t.client = AsyncMock()
        t.client.post = AsyncMock(side_effect=httpx.HTTPError("fail"))
        t.consecutive_failures = 4

        await t.add(_make_entry())
        await t.flush()

        assert t.consecutive_failures == 5
        assert t.circuit_breaker_until > time.time()


class TestBatchTransportClose:
    @pytest.mark.asyncio
    async def test_close_flushes_and_closes_client(self):
        t = BatchTransport(
            ingest_url="http://x/ingest", api_key="k", agent_id="a",
        )
        t.client = AsyncMock()
        t.client.post = AsyncMock(return_value=_ok_response())
        t.client.aclose = AsyncMock()

        await t.add(_make_entry())
        await t.close()

        # Should have flushed
        t.client.post.assert_called_once()
        # Should have closed the HTTP client
        t.client.aclose.assert_called_once()
