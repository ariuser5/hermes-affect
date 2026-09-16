"""Small fake Hermes context used to test the public registration adapter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class FakeStructuredResult:
    def __init__(self, parsed: Any = None, text: str = "") -> None:
        self.parsed = parsed
        self.text = text


class FakePluginLlm:
    def __init__(
        self,
        response: FakeStructuredResult | None = None,
        *,
        error: Exception | None = None,
        on_call: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.response = response or FakeStructuredResult()
        self.error = error
        self.on_call = on_call
        self.calls: list[dict[str, Any]] = []

    def complete_structured(self, **kwargs: Any) -> FakeStructuredResult:
        self.calls.append(kwargs)
        if self.on_call is not None:
            self.on_call(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class FakeHermesContext:
    def __init__(self, *, llm: Any = None, **config: Any) -> None:
        self.config = config
        self.llm = llm
        self.hooks: dict[str, Callable[..., Any]] = {}
        self.commands: dict[str, tuple[Callable[..., Any], str]] = {}

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def register_hook(self, name: str, callback: Callable[..., Any]) -> None:
        self.hooks[name] = callback

    def register_command(
        self, name: str, callback: Callable[..., Any], description: str
    ) -> None:
        self.commands[name] = (callback, description)

    def emit(self, name: str, **kwargs: Any) -> Any:
        return self.hooks[name](**kwargs)

    def invoke_command(self, name: str, *args: Any, **kwargs: Any) -> Any:
        callback, _description = self.commands[name]
        return callback(*args, **kwargs)
