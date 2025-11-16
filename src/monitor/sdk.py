"""High-level API for Okimotus Monitor."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Dict, Mapping, Optional

from .serial_reader import SerialLine, SerialReader
from .tui import on_quit, shutdown


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

    def readline(self, timeout: Optional[float] = None) -> Optional[SerialLine]:
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
    return SerialPort(port=port, baudrate=baudrate, serial_kwargs=serial_kwargs)


def serve(port_configs: Mapping[str, int], handler: Callable[[str, SerialLine], None], *, poll_interval: float = 0.05):
    if not port_configs:
        raise ValueError("At least one port configuration is required")

    stop_event = threading.Event()
    remove_quit_callback = on_quit(stop_event.set)

    ports = {name: get_port(name, baudrate) for name, baudrate in port_configs.items()}

    try:
        while not stop_event.is_set():
            for name, port in ports.items():
                line = port.readline(timeout=poll_interval)
                if line is not None:
                    handler(name, line)
            if stop_event.is_set():
                break
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        remove_quit_callback()
        for port in ports.values():
            port.close()
        shutdown()


__all__ = ["SerialPort", "get_port", "serve"]
