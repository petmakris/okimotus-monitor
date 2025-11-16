#!/usr/bin/env python3
"""Axis monitor demo translated from the legacy YAML configuration."""

from __future__ import annotations

from typing import Dict, List, Optional

from monitor import get_port, out, shutdown


def to_int(line, index: int, default: int = 0) -> int:
    raw = line.get(index)
    if raw is None:
        return default
    try:
        return int(str(raw).strip() or 0)
    except ValueError:
        return default


def to_float(line, index: int, default: float = 0.0) -> float:
    raw = line.get(index)
    if raw is None:
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        try:
            return float(int(str(raw).strip(), 10))
        except ValueError:
            return default


def axis_observables(line) -> Dict[str, float]:
    counts = to_float(line, 1)
    return {
        "motor_revs": counts / 1600.0,
        "radial_degrees": (counts / 1600.0) * 10.0,
    }


def command_observables(line) -> Dict[str, object]:
    counts = to_float(line, 2)
    units_per_rev = to_float(line, 4)
    dynamic_scale = to_float(line, 5, default=10.0)

    unit_selector = to_int(line, 1)
    unit_label = {
        0: "mm",
        1: "in",
        2: "deg",
    }.get(unit_selector, "UNKNOWN")

    return {
        "units": unit_label,
        "radial_degrees": (counts / 1600.0) * dynamic_scale,
        "units_per_rev": units_per_rev,
    }


def format_rows(axis: Optional[Dict[str, float]], command: Optional[Dict[str, object]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    if axis:
        rows.append({"label": "Motor Revs (Axis)", "value": f"{axis['motor_revs']:.3f} rev"})
        rows.append({"label": "Radial Degrees (Axis)", "value": f"{axis['radial_degrees']:.3f} deg"})

    if command:
        rows.append({"label": "Units", "value": command['units']})
        rows.append({"label": "Radial Degrees (Cmd)", "value": f"{command['radial_degrees']:.3f} deg"})
        rows.append({"label": "Units / Motor Rev", "value": f"{command['units_per_rev']:.3f}"})

    return rows


def main():
    axis_port = get_port('/dev/ttyUSB0', baudrate=115200)
    command_port = get_port('/dev/ttyUSB1', baudrate=115200)

    latest_axis: Optional[Dict[str, float]] = None
    latest_command: Optional[Dict[str, object]] = None

    try:
        while True:
            axis_line = axis_port.readline(timeout=0.05)
            if axis_line:
                latest_axis = axis_observables(axis_line)

            command_line = command_port.readline(timeout=0.05)
            if command_line:
                latest_command = command_observables(command_line)

            if not latest_axis and not latest_command:
                continue

            out(format_rows(latest_axis, latest_command))
    finally:
        shutdown()
        axis_port.close()
        command_port.close()


if __name__ == '__main__':
    main()
