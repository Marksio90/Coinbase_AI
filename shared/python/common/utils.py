"""Common utility helpers."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def async_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 3.0,
) -> T:
    """Retry async operation with exponential backoff + jitter."""

    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    current_delay = base_delay
    last_exception: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except Exception as exc:  # intentionally broad for external IO reliability
            last_exception = exc
            if attempt == attempts:
                break
            sleep_for = min(current_delay, max_delay) + random.uniform(0.0, 0.1)
            await asyncio.sleep(sleep_for)
            current_delay *= 2
    assert last_exception is not None
    raise last_exception
