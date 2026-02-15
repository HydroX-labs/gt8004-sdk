"""Tests for tool name extraction utilities."""

import json
import pytest

from gt8004.middleware._extract import (
    BODY_LIMIT,
    extract_mcp_tool_name,
    extract_a2a_tool_name,
    extract_http_tool_name,
    extract_tool_name,
)


class TestExtractMCPToolName:
    def test_valid_tools_call(self):
        body = json.dumps({"method": "tools/call", "params": {"name": "search"}})
        assert extract_mcp_tool_name(body) == "search"

    def test_different_method(self):
        body = json.dumps({"method": "resources/list", "params": {"name": "foo"}})
        assert extract_mcp_tool_name(body) is None

    def test_missing_params(self):
        body = json.dumps({"method": "tools/call"})
        assert extract_mcp_tool_name(body) is None

    def test_none_body(self):
        assert extract_mcp_tool_name(None) is None

    def test_empty_body(self):
        assert extract_mcp_tool_name("") is None

    def test_invalid_json(self):
        assert extract_mcp_tool_name("not json") is None

    def test_non_dict_json(self):
        assert extract_mcp_tool_name("[1, 2, 3]") is None


class TestExtractA2AToolName:
    def test_skill_id_from_body(self):
        body = json.dumps({"skill_id": "translate", "input": "hello"})
        assert extract_a2a_tool_name(body, "/a2a/tasks") == "translate"

    def test_fallback_to_path(self):
        assert extract_a2a_tool_name(None, "/a2a/tasks/send") == "send"

    def test_fallback_to_path_with_trailing_slash(self):
        assert extract_a2a_tool_name(None, "/a2a/tasks/send/") == "send"

    def test_body_without_skill_id(self):
        body = json.dumps({"input": "hello"})
        assert extract_a2a_tool_name(body, "/a2a/run") == "run"

    def test_invalid_json_fallback_to_path(self):
        assert extract_a2a_tool_name("bad json", "/api/search") == "search"

    def test_empty_body_fallback(self):
        assert extract_a2a_tool_name("", "/tasks") == "tasks"


class TestExtractHTTPToolName:
    def test_simple_path(self):
        assert extract_http_tool_name("/api/search") == "search"

    def test_trailing_slash(self):
        assert extract_http_tool_name("/api/search/") == "search"

    def test_root_path(self):
        assert extract_http_tool_name("/") == ""

    def test_deep_path(self):
        assert extract_http_tool_name("/v1/api/tools/generate") == "generate"


class TestExtractToolName:
    def test_mcp_protocol(self):
        body = json.dumps({"method": "tools/call", "params": {"name": "search"}})
        assert extract_tool_name("mcp", body, "/mcp") == "search"

    def test_a2a_protocol(self):
        body = json.dumps({"skill_id": "translate"})
        assert extract_tool_name("a2a", body, "/a2a") == "translate"

    def test_none_protocol_uses_http(self):
        assert extract_tool_name(None, None, "/api/search") == "search"

    def test_unknown_protocol_uses_http(self):
        assert extract_tool_name("other", None, "/api/search") == "search"


class TestBodyLimit:
    def test_body_limit_is_16kb(self):
        assert BODY_LIMIT == 16384
