"""Function Registry — Plugin system for LECAT indicator functions.

Provides decorator-based and programmatic registration of indicator
functions. Each function receives a MarketContext and returns a
FunctionResult.

Design pattern: Service Locator + Decorator Registration.
See docs/03_Function_Registry_API.md for full specification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from lecat.context import MarketContext


@dataclass(frozen=True)
class FunctionResult:
    """Standard return type for all registry functions.

    Attributes:
        value: The computed numeric value (None if invalid).
        error: Error message if computation failed.
        is_valid: False if value should be treated as NaN/missing.
    """

    value: float | None
    error: str | None = None
    is_valid: bool = True

    @staticmethod
    def success(value: float) -> FunctionResult:
        """Create a successful result."""
        return FunctionResult(value=value, is_valid=True)

    @staticmethod
    def insufficient_data() -> FunctionResult:
        """Create an insufficient-data result (warmup period)."""
        return FunctionResult(value=None, is_valid=False, error="Insufficient data")

    @staticmethod
    def from_error(message: str) -> FunctionResult:
        """Create an error result."""
        return FunctionResult(value=None, is_valid=False, error=message)


@dataclass(frozen=True)
class FunctionMeta:
    """Metadata about a registered function.

    Used by the optimizer for introspection and by the evaluator
    for argument validation.
    """

    name: str
    description: str
    arg_schema: list[dict[str, Any]]
    min_bars_required: Callable[[dict[str, Any]], int]
    return_type: str = "float"


# Type alias for handler functions
HandlerFn = Callable[[dict[str, Any], MarketContext], FunctionResult]


class RegistryError(Exception):
    """Raised on registry-related errors (duplicate name, locked, etc.)."""


class FunctionRegistry:
    """Plugin registry mapping function names to their handlers.

    Usage:
        registry = FunctionRegistry()

        @registry.register(name="RSI", arg_schema=[...])
        def rsi_handler(args, context):
            ...

        registry.lock()
        handler = registry.get_handler("RSI")
    """

    def __init__(self) -> None:
        self._handlers: dict[str, HandlerFn] = {}
        self._metadata: dict[str, FunctionMeta] = {}
        self._locked = False

    def register(
        self,
        name: str,
        description: str = "",
        arg_schema: list[dict[str, Any]] | None = None,
        min_bars_required: Callable[[dict[str, Any]], int] | None = None,
    ) -> Callable[[HandlerFn], HandlerFn]:
        """Decorator to register a function handler.

        Args:
            name: Unique function name (e.g., "RSI").
            description: Human-readable description.
            arg_schema: List of argument definitions.
            min_bars_required: Callable returning minimum bars needed.

        Returns:
            Decorator that registers the function and returns it unchanged.

        Raises:
            RegistryError: If name is already registered or registry is locked.
        """

        def decorator(fn: HandlerFn) -> HandlerFn:
            self.register_handler(
                name=name,
                handler=fn,
                description=description,
                arg_schema=arg_schema or [],
                min_bars_required=min_bars_required or (lambda _: 1),
            )
            return fn

        return decorator

    def register_handler(
        self,
        name: str,
        handler: HandlerFn,
        description: str = "",
        arg_schema: list[dict[str, Any]] | None = None,
        min_bars_required: Callable[[dict[str, Any]], int] | None = None,
    ) -> None:
        """Programmatically register a function handler.

        Raises:
            RegistryError: If name is already registered or registry is locked.
        """
        if self._locked:
            raise RegistryError(
                f"Cannot register '{name}': registry is locked"
            )
        if name in self._handlers:
            raise RegistryError(
                f"Cannot register '{name}': name already registered"
            )

        self._handlers[name] = handler
        self._metadata[name] = FunctionMeta(
            name=name,
            description=description,
            arg_schema=arg_schema or [],
            min_bars_required=min_bars_required or (lambda _: 1),
        )

    def get_handler(self, name: str) -> HandlerFn:
        """Return the handler callable for a given function name.

        Raises:
            RegistryError: If name is not registered.
        """
        if name not in self._handlers:
            raise RegistryError(f"Unknown function: '{name}'")
        return self._handlers[name]

    def get_function_meta(self, name: str) -> FunctionMeta:
        """Return metadata for a specific function.

        Raises:
            RegistryError: If name is not registered.
        """
        if name not in self._metadata:
            raise RegistryError(f"Unknown function: '{name}'")
        return self._metadata[name]

    def get_available_functions(self) -> list[FunctionMeta]:
        """Return metadata for all registered functions."""
        return list(self._metadata.values())

    def has_function(self, name: str) -> bool:
        """Check if a function is registered."""
        return name in self._handlers

    def lock(self) -> None:
        """Prevent further registrations. Called before evaluation."""
        self._locked = True

    @property
    def is_locked(self) -> bool:
        return self._locked
