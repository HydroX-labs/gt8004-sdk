# GT8004 Python SDK

Official Python SDK for [GT8004](https://github.com/HydroX-labs/gt8004) - AI Agent Analytics & Observability Platform.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
pip install git+https://github.com/HydroX-labs/gt8004-sdk.git
```

## Quick Start

### MCP Server

```python
logger = GT8004Logger(
    agent_id="your-agent-id",
    api_key="your-api-key",
    protocol="mcp"
)
logger.transport.start_auto_flush()

app = FastAPI()
app.add_middleware(GT8004Middleware, logger=logger)
# Automatically extracts tool names from JSON-RPC tools/call requests
```

### A2A Server

```python
logger = GT8004Logger(
    agent_id="your-agent-id",
    api_key="your-api-key",
    protocol="a2a"
)
logger.transport.start_auto_flush()

app = FastAPI()
app.add_middleware(GT8004Middleware, logger=logger)
# Automatically extracts skill_id from A2A request bodies
```

Your analytics are now live at `https://gt8004.xyz/agents/{agent-id}` with protocol-specific breakdowns.

## Features

- Zero-config FastAPI middleware
- Protocol-aware logging (MCP, A2A)
- Automatic tool/skill name extraction per protocol
- Non-blocking async transport
- Auto-retry with exponential backoff
- Circuit breaker protection

## Protocol Support

| Protocol | Tool Name Source | Example |
|----------|----------------|---------|
| *(none)* | URL path last segment | `/api/search` -> `search` |
| `mcp` | JSON-RPC `tools/call` params | `{"method":"tools/call","params":{"name":"search"}}` -> `search` |
| `a2a` | Request body `skill_id` | `{"skill_id":"translate"}` -> `translate` |

## Documentation

See [examples/](examples/) for complete examples.

## License

MIT - see [LICENSE](LICENSE)
