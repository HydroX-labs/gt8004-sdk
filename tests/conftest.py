"""Shared test fixtures for GT8004 SDK tests."""

import asyncio
import pytest


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
