#!/usr/bin/env python3
"""Axis monitor demo translated from the legacy YAML configuration."""

from __future__ import annotations

from typing import Iterable, Mapping, Optional

from monitor import SerialLine, run


def to_int(line, index: int, default: int = 0) -> int:
    if line is None:
        return default
    raw = line.get(index)
    if raw is None:
        return default
    try:
        return int(str(raw).strip() or 0)
    except ValueError:
        return default


def to_float(line, index: int, default: float = 0.0) -> float:
    if line is None:
        return default
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


def parse_units(value: int) -> str:
    if value == 0:
        return "mm"
    if value == 1:
        return "in"
    if value == 2:
        return "deg"
    return "--"


def render(lines: Mapping[str, Optional[SerialLine]]) -> Iterable[Mapping[str, object]]:
    rows = [
        {"label": "Encoder time", "value": "--"},
        {"label": "Motor Revs (Encoder)", "value": "--"},
        {"label": "Radial Degrees (Encoder)", "value": "--"},

        {"label": "Command time", "value": "--"},
        {"label": "Units", "value": "--"},
        {"label": "Radial Degrees (Cmd)", "value": "--"},
    ]

    encoder = lines.get("encoder")
    command = lines.get("command")

    if (encoder is None) and (command is None):
        return rows

    if encoder:
        encoder_time = to_int(encoder, index=0)
        encoder_counts = to_float(encoder, 1)
        encoder_motor_revs = encoder_counts / 1600.0
        encoder_radial_degrees = (encoder_counts / 1600.0) * 10.0

        rows[0]["value"] = f"{encoder_time}s"
        rows[1]["value"] = f"{encoder_motor_revs:.3f} rev"
        rows[2]["value"] = f"{encoder_radial_degrees:.3f} deg"

    if command:
        command_time = to_int(command, index=0)
        command_counts = to_float(command, index=2)
        command_dynamic_scale = to_float(command, index=5, default=10.0)
        radial_degrees = (command_counts / 1600.0) * command_dynamic_scale

        rows[3]["value"] = f"{command_time}s"
        rows[4]["value"] = parse_units(to_int(command, 1))
        rows[5]["value"] = f"{radial_degrees:.3f} deg"

    return rows


if __name__ == '__main__':
    run(
        {
            "encoder": {"device": "/dev/ttyUSB0", "baudrate": 115200},
            "command": {"device": "/dev/ttyUSB1", "baudrate": 115200},
        },
        render=render,
        poll_interval=0.5,
    )
