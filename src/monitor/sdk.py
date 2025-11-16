"""High-level API for Okimotus Monitor."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Mapping, Optional

from .serial_reader import SerialLine, SerialReader
from .tui import on_quit, out, shutdown


@dataclass(frozen=True)
class PortConfig:
    """Describe how to open a hardware port."""

    device: str
    baudrate: int = 115200
    serial_kwargs: Optional[Dict[str, object]] = None


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


def _normalize_port_configs(port_configs: Mapping[str, object]) -> Dict[str, PortConfig]:
    """Coerce the various user-friendly shapes into PortConfig objects."""
    normalized: Dict[str, PortConfig] = {}
    for name, raw in port_configs.items():
        if isinstance(raw, PortConfig):
            config = raw
        elif isinstance(raw, str):
            config = PortConfig(device=raw)
        elif isinstance(raw, (list, tuple)):
            if not raw:
                raise ValueError(f"Port entry '{name}' is empty")
            device = str(raw[0])
            baudrate = int(raw[1]) if len(raw) > 1 else 115200
            kwargs = raw[2] if len(raw) > 2 else None
            if kwargs is not None and not isinstance(kwargs, Mapping):
                raise TypeError(f"serial_kwargs for '{name}' must be a mapping, got {type(kwargs).__name__}")
            serial_kwargs = dict(kwargs) if kwargs else None
            config = PortConfig(device=device, baudrate=baudrate, serial_kwargs=serial_kwargs)
        elif isinstance(raw, Mapping):
            device = str(raw.get("device") or raw.get("port") or name)
            baudrate = int(raw.get("baudrate") or raw.get("baud") or 115200)
            kwargs = raw.get("serial_kwargs") or raw.get("kwargs")
            if kwargs is not None and not isinstance(kwargs, Mapping):
                raise TypeError(f"serial_kwargs for '{name}' must be a mapping, got {type(kwargs).__name__}")
            serial_kwargs = dict(kwargs) if kwargs else None
            config = PortConfig(device=device, baudrate=baudrate, serial_kwargs=serial_kwargs)
        elif isinstance(raw, int):
            config = PortConfig(device=name, baudrate=int(raw))
        else:
            raise TypeError(f"Unsupported port config for '{name}': {raw!r}")
        normalized[name] = config
    if not normalized:
        raise ValueError("At least one port configuration is required")
    return normalized


def serve(
    port_configs: Mapping[str, object],
    handler: Callable[[str, SerialLine], None],
    *,
    poll_interval: float = 0.05,
    stop_event: Optional[threading.Event] = None,
):
    normalized = _normalize_port_configs(port_configs)

    loop_stop = stop_event or threading.Event()
    remove_quit_callback = on_quit(loop_stop.set)

    ports = {
        name: get_port(config.device, config.baudrate, **(config.serial_kwargs or {}))
        for name, config in normalized.items()
    }

    sleep_interval = max(0.0, poll_interval)

    try:
        while not loop_stop.is_set():
            did_work = False
            for name, port in ports.items():
                line = port.readline(timeout=0)
                if line is not None:
                    did_work = True
                    handler(name, line)
            if loop_stop.is_set():
                break
            if not did_work and sleep_interval:
                loop_stop.wait(sleep_interval)
    except KeyboardInterrupt:
        loop_stop.set()
    finally:
        loop_stop.set()
        remove_quit_callback()
        for port in ports.values():
            port.close()
        shutdown()
    return loop_stop


def run(
    port_configs: Mapping[str, object],
    render: Callable[[Mapping[str, Optional[SerialLine]]], Optional[Iterable[Mapping[str, object]]]],
    *,
    poll_interval: float = 0.05,
    initial_output: Optional[Iterable[Mapping[str, object]]] = None,
):
    """
    High-level helper that manages the serial loop and dashboard updates.

    Args:
        port_configs: Mapping of alias -> configuration. Each value can be a
            baudrate int, a device path string, a dict with "device"/"baudrate",
            a (device, baudrate[, serial_kwargs]) tuple, or a PortConfig.
        render: Callable that receives a snapshot of the latest lines for every
            alias and returns the rows to show via monitor.out. Returning None
            skips UI updates. Raise StopIteration to request a graceful exit.
        poll_interval: Maximum time to wait for new data per port read call.
        initial_output: Optional rows rendered before any serial data arrives.
    """

    normalized = _normalize_port_configs(port_configs)
    latest: Dict[str, Optional[SerialLine]] = {name: None for name in normalized}
    loop_stop = threading.Event()

    if initial_output is not None:
        out(initial_output)

    def _snapshot() -> Dict[str, Optional[SerialLine]]:
        return {name: (line.copy() if line is not None else None) for name, line in latest.items()}

    def handler(name: str, line: SerialLine):
        latest[name] = line
        snapshot = _snapshot()
        try:
            rows = render(snapshot)
        except StopIteration:
            loop_stop.set()
            return
        if rows is not None:
            out(rows)

    return serve(normalized, handler, poll_interval=poll_interval, stop_event=loop_stop)


__all__ = ["SerialPort", "PortConfig", "get_port", "run", "serve"]
