from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class Event:
    name: str
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """Async observer pattern implementation."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._subscribers[event_name].append(handler)

    async def publish(self, name: str, payload: dict[str, Any]) -> Event:
        event = Event(name=name, payload=payload)
        for handler in [*self._subscribers.get(name, []), *self._subscribers.get("*", [])]:
            await handler(event)
        return event

