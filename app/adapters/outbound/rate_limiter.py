import asyncio
import time
from collections.abc import Awaitable, Callable


class RateLimiter:
    """限制連續請求的最短間隔，同時多個請求會依序排隊"""

    def __init__(
        self,
        min_interval: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._next_at: float | None = None

    async def wait(self) -> None:
        """等到可以發送下一個請求為止"""
        async with self._lock:
            if self._next_at is not None:
                delay = self._next_at - self._clock()
                if delay > 0:
                    await self._sleep(delay)
            self._next_at = self._clock() + self.min_interval
