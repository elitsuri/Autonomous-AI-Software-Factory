from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class ServiceContainer:
    """Tiny dependency injection container for long-lived application services."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[ServiceContainer], Any]] = {}
        self._instances: dict[str, Any] = {}

    def register_factory(self, key: str, factory: Callable[["ServiceContainer"], T]) -> None:
        self._factories[key] = factory
        self._instances.pop(key, None)

    def register_instance(self, key: str, instance: T) -> None:
        self._instances[key] = instance

    def resolve(self, key: str, expected_type: type[T] | None = None) -> T:
        if key not in self._instances:
            if key not in self._factories:
                raise KeyError(f"No service registered for {key!r}")
            self._instances[key] = self._factories[key](self)
        instance = self._instances[key]
        if expected_type is not None and not isinstance(instance, expected_type):
            raise TypeError(f"Service {key!r} is {type(instance)!r}, expected {expected_type!r}")
        return instance

