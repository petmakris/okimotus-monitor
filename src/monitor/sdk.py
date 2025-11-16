"""High-level API for Okimotus Monitor.

This module provides two essentials:
- `get_port()` for acquiring a streaming serial port whose `readline()` method
  yields parsed CSV dictionaries.
- `Display` helpers exposed via `monitor.out()` (implemented in `display.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .serial_reader import SerialLine, SerialReader


@dataclass
class SerialPort:
    """User-facing wrapper that exposes a simple `readline()` method."""

    port: str
    baudrate: int = 115200
    serial_kwargs: Optional[Dict[str, object]] = None

    def __post_init__(self):
        kwargs = self.serial_kwargs or {}
        self._reader = SerialReader(self.port, self.baudrate, **kwargs)
        self._closed = False

    def readline(self, timeout: Optional[float] = 0.15) -> Optional[SerialLine]:
        """Return the next parsed line (Mapping of index -> string).

        When no data is available before `timeout`, returns ``None``.
        Passing ``timeout=None`` blocks indefinitely until data arrives.
        """

        if self._closed:
            raise RuntimeError("SerialPort is closed")
        return self._reader.read_line(timeout=timeout)

    def close(self):
        if not self._closed:
            self._reader.close()
            self._closed = True

    def __enter__(self) -> "SerialPort":
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def get_port(port: str, baudrate: int = 115200, **serial_kwargs) -> SerialPort:
    """Factory that returns a `SerialPort` instance ready for `.readline()` calls."""

    return SerialPort(port=port, baudrate=baudrate, serial_kwargs=serial_kwargs)


