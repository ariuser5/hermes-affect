"""Small fake Hermes context used to test the public registration adapter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class FakeHermesContext:
    def __init__(self, **config: Any) -> None:
        self.config = config
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
