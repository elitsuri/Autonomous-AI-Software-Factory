import pytest

from core.container import ServiceContainer
from core.events import EventBus
from core.security import SecurityService


def test_security_hashes_passwords_and_round_trips_jwt() -> None:
    service = SecurityService(secret_key="test-secret-key-with-more-than-32-characters")
    password_hash = service.hash_password("correct-horse-battery-staple")

    assert service.verify_password("correct-horse-battery-staple", password_hash)
    assert not service.verify_password("wrong-password", password_hash)

    token = service.create_access_token(subject="operator@example.com", roles=["admin"])
    payload = service.decode_access_token(token)
    assert payload["sub"] == "operator@example.com"
    assert payload["roles"] == ["admin"]
    assert not service.verify_password("password", "not-a-valid-hash")


def test_container_resolves_factories_once() -> None:
    container = ServiceContainer()
    calls = 0

    def factory(_container: ServiceContainer) -> list[str]:
        nonlocal calls
        calls += 1
        return ["service"]

    container.register_factory("names", factory)

    assert container.resolve("names", list) == ["service"]
    assert container.resolve("names", list) == ["service"]
    assert calls == 1


def test_container_reports_missing_or_wrongly_typed_services() -> None:
    container = ServiceContainer()
    container.register_instance("count", 3)

    with pytest.raises(KeyError):
        container.resolve("missing")

    with pytest.raises(TypeError):
        container.resolve("count", list)


@pytest.mark.asyncio
async def test_event_bus_notifies_specific_and_wildcard_subscribers() -> None:
    event_bus = EventBus()
    received = []

    async def receive(event):
        received.append((event.name, event.payload))

    event_bus.subscribe("agent.finished", receive)
    event_bus.subscribe("*", receive)

    await event_bus.publish("agent.finished", {"agent": "reviewer"})

    assert received == [
        ("agent.finished", {"agent": "reviewer"}),
        ("agent.finished", {"agent": "reviewer"}),
    ]
