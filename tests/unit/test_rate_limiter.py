import asyncio

import pytest

from app.adapters.outbound.rate_limiter import RateLimiter


class FakeTime:
    """可手動推進的時鐘，sleep 只推進時間並記錄等待秒數"""

    def __init__(self) -> None:
        self.now = 100.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def make_limiter(fake: FakeTime, interval: float = 0.5) -> RateLimiter:
    return RateLimiter(interval, clock=fake.clock, sleep=fake.sleep)


async def test_first_request_does_not_wait():
    fake = FakeTime()

    await make_limiter(fake).wait()

    assert fake.sleeps == []


async def test_waits_remaining_interval():
    fake = FakeTime()
    limiter = make_limiter(fake)

    await limiter.wait()
    fake.now += 0.2
    await limiter.wait()

    assert fake.sleeps == [pytest.approx(0.3)]


async def test_no_wait_after_interval_passed():
    fake = FakeTime()
    limiter = make_limiter(fake)

    await limiter.wait()
    fake.now += 0.5
    await limiter.wait()

    assert fake.sleeps == []


async def test_concurrent_requests_are_queued():
    fake = FakeTime()
    limiter = make_limiter(fake)
    started: list[float] = []

    async def request() -> None:
        await limiter.wait()
        started.append(fake.now)

    await asyncio.gather(*(request() for _ in range(3)))

    assert started == [100.0, 100.5, 101.0]
