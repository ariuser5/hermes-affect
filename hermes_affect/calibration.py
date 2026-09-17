"""Compatibility entry point for the calibration CLI."""

from .tools.calibration import main

__all__ = ["main"]


if __name__ == "__main__":
    main()
