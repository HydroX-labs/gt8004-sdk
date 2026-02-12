"""Main GT8004 logger class."""

from .transport import BatchTransport
from .types import RequestLogEntry


class GT8004Logger:
    """
    Main logger class for GT8004 SDK.

    Usage:
        logger = GT8004Logger(
            agent_id="your-agent-id",
            api_key="your-api-key"
        )
        logger.transport.start_auto_flush()

        # In FastAPI middleware
        await logger.log(entry)

        # On shutdown
        await logger.close()
    """

    def __init__(
        self,
        agent_id: str,
        api_key: str,
        ingest_url: str = "http://localhost:9093/v1/ingest",
        batch_size: int = 50,
        flush_interval: float = 5.0,
    ):
        """
        Initialize the GT8004 logger.

        Args:
            agent_id: Your GT8004 agent ID
            api_key: Your GT8004 API key
            ingest_url: GT8004 ingest API endpoint (default: localhost:9093)
            batch_size: Number of entries before auto-flush (default: 50)
            flush_interval: Seconds between auto-flushes (default: 5.0)
        """
        self.agent_id = agent_id
        self.api_key = api_key
        self.transport = BatchTransport(
            ingest_url=ingest_url,
            api_key=api_key,
            agent_id=agent_id,
            batch_size=batch_size,
            flush_interval=flush_interval,
        )

    async def log(self, entry: RequestLogEntry) -> None:
        """
        Add a log entry to the batch queue.

        Args:
            entry: The RequestLogEntry to log
        """
        await self.transport.add(entry)

    async def flush(self) -> None:
        """Flush all pending logs immediately."""
        await self.transport.flush()

    async def close(self) -> None:
        """Close the logger and flush pending logs."""
        await self.transport.close()
