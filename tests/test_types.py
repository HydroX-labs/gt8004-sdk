"""Tests for GT8004 SDK types."""

import pytest
from pydantic import ValidationError

from gt8004.types import RequestLogEntry, LogBatch, _to_camel


class TestCamelCase:
    def test_single_word(self):
        assert _to_camel("method") == "method"

    def test_two_words(self):
        assert _to_camel("status_code") == "statusCode"

    def test_three_words(self):
        assert _to_camel("request_body_size") == "requestBodySize"

    def test_x402_field(self):
        assert _to_camel("x402_amount") == "x402Amount"


class TestRequestLogEntry:
    def test_required_fields(self):
        entry = RequestLogEntry(
            request_id="r1", method="GET", path="/test",
            status_code=200, response_ms=5.0,
        )
        assert entry.request_id == "r1"
        assert entry.source == "sdk"

    def test_protocol_mcp(self):
        entry = RequestLogEntry(
            request_id="r1", method="GET", path="/",
            status_code=200, response_ms=0, protocol="mcp",
        )
        assert entry.protocol == "mcp"

    def test_protocol_a2a(self):
        entry = RequestLogEntry(
            request_id="r1", method="GET", path="/",
            status_code=200, response_ms=0, protocol="a2a",
        )
        assert entry.protocol == "a2a"

    def test_protocol_none(self):
        entry = RequestLogEntry(
            request_id="r1", method="GET", path="/",
            status_code=200, response_ms=0,
        )
        assert entry.protocol is None

    def test_invalid_protocol(self):
        with pytest.raises(ValidationError):
            RequestLogEntry(
                request_id="r1", method="GET", path="/",
                status_code=200, response_ms=0, protocol="http",
            )

    def test_timestamp_auto_generated(self):
        entry = RequestLogEntry(
            request_id="r1", method="GET", path="/",
            status_code=200, response_ms=0,
        )
        assert entry.timestamp.endswith("Z")

    def test_camel_case_serialization(self):
        entry = RequestLogEntry(
            request_id="r1", method="GET", path="/",
            status_code=200, response_ms=5.0,
            tool_name="search",
        )
        data = entry.model_dump(by_alias=True)
        assert "requestId" in data
        assert "statusCode" in data
        assert "responseMs" in data
        assert "toolName" in data

    def test_exclude_none(self):
        entry = RequestLogEntry(
            request_id="r1", method="GET", path="/",
            status_code=200, response_ms=0,
        )
        data = entry.model_dump(by_alias=True, exclude_none=True)
        assert "customerId" not in data
        assert "toolName" not in data
        assert "requestBody" not in data


class TestLogBatch:
    def test_batch_structure(self):
        entries = [
            RequestLogEntry(
                request_id="r1", method="GET", path="/",
                status_code=200, response_ms=0,
            )
        ]
        batch = LogBatch(agent_id="agent-123", entries=entries)
        assert batch.agent_id == "agent-123"
        assert batch.sdk_version == "python-0.2.0"
        assert len(batch.entries) == 1

    def test_batch_serialization(self):
        entries = [
            RequestLogEntry(
                request_id="r1", method="GET", path="/",
                status_code=200, response_ms=0,
            )
        ]
        batch = LogBatch(agent_id="a", entries=entries)
        data = batch.model_dump(by_alias=True, exclude_none=True)
        assert "agentId" in data
        assert "sdkVersion" in data
        assert "entries" in data
