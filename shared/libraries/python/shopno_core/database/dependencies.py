"""Startup dependency readiness helpers for Shopnoltd services."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

log = logging.getLogger(__name__)


async def wait_for_dependencies(
    service_name: str,
    database_check: Callable[[], Awaitable[None]],
    redis_client,
    *,
    max_attempts: int = 60,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
) -> None:
    """Wait for PostgreSQL and Redis during process startup.

    A pod may start before its data dependencies after a node/runtime restart.
    Retry bounded startup checks so transient dependency outages do not turn
    into CrashLoopBackOff storms. The final exception is re-raised so invalid
    credentials/configuration still fail loudly after the bounded wait.
    """
    delay = initial_delay
    for attempt in range(1, max_attempts + 1):
        try:
            await database_check()
            await redis_client.ping()
            if attempt > 1:
                log.info(
                    "%s startup dependencies became ready after %d attempts",
                    service_name,
                    attempt,
                )
            return
        except Exception:
            if attempt >= max_attempts:
                log.exception(
                    "%s startup dependencies remained unavailable after %d attempts",
                    service_name,
                    attempt,
                )
                raise
            log.warning(
                "%s startup dependencies unavailable (attempt %d/%d); retrying in %.1fs",
                service_name,
                attempt,
                max_attempts,
                delay,
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)
