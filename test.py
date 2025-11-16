#!/usr/bin/env python3
"""Axis monitor demo translated from the legacy YAML configuration."""

from __future__ import annotations

from typing import Iterable, Mapping, Optional

from monitor import SerialLine, run


class ParseError(ValueError):
    """Raised when incoming serial data cannot be parsed."""


_last_parse_error: Optional[str] = None


def _coerce_text(value: object, index: int) -> str:
    text = str(value).replace("\x00", "").strip()
    if not text:
        raise ParseError(f"Empty value at index {index}")
    return text


def to_int(line, index: int) -> int:
    if line is None:
        raise ParseError(f"Missing line while parsing int at index {index}")
    raw = line.get(index)
    if raw is None:
        raise ParseError(f"Missing value at index {index}")
    text = _coerce_text(raw, index)
    try:
        return int(text, 10)
    except ValueError as exc:
        raise ParseError(f"Invalid integer at index {index}: {raw!r}") from exc


def to_float(line, index: int) -> float:
    if line is None:
        raise ParseError(f"Missing line while parsing float at index {index}")
    raw = line.get(index)
    if raw is None:
        raise ParseError(f"Missing value at index {index}")
    text = _coerce_text(raw, index)
    try:
        return float(text)
    except ValueError:
        try:
            return float(int(text, 10))
        except ValueError as exc:
            raise ParseError(f"Invalid float at index {index}: {raw!r}") from exc


def parse_units(value: int) -> str:
    if value == 0:
        return "mm"
    if value == 1:
        return "in"
    if value == 2:
        return "deg"
    return "--"


def render(lines: Mapping[str, Optional[SerialLine]]) -> Optional[Iterable[Mapping[str, object]]]:
    global _last_parse_error

    rows = [
        # Encoder
        {"label": "Time", "value": "--", "unit": "s"},
        {"label": "Motor Revs", "value": "--", "unit": "rev"},
        {"label": "Radial Degrees", "value": "--", "unit": "deg"},


        # Command
        {"label": "Time", "value": "--", "unit": "s"},
        {"label": "Units", "value": "--"},

        {"label": "Commanded Steps", "value": "--", "unit": "steps"},
        {"label": "Current Position in Units", "value": "--", "unit": "units"},

        {"label": "Units per Revolution", "value": "--", "unit": "units/rev"},


        
    ]

    encoder = lines.get("encoder")
    command = lines.get("command")

    try:
        if encoder:
            encoder_time = to_int(encoder, index=0)
            encoder_counts = to_float(encoder, 1)
            encoder_motor_revs = encoder_counts / 1600.0
            encoder_radial_degrees = (encoder_counts / 1600.0) * 10.0

            rows[0]["value"] = str(encoder_time)
            rows[1]["value"] = f"{encoder_motor_revs:.3f}"
            rows[2]["value"] = f"{encoder_radial_degrees:.3f}"

            # 2725,  -- time
            # 0,     -- units
            # 2700,  -- commanded steps
            # 8.44,  -- current position in units
            # 5.00   -- units per revolution

        if command:
            command_time              = to_int(command, index=0)
            command_units             = to_int(command, 1)
            command_steps             = to_float(command, index=2)
            command_curr_pos_in_units = to_float(command, index=3)
            command_units_per_rev     = to_float(command, index=4)

            rows[3]["value"] = str(command_time)
            rows[4]["value"] = parse_units(command_units)

            rows[5]["value"] = f"{command_steps}"
            rows[6]["value"] = f"{command_curr_pos_in_units:.3f}"
            
            rows[7]["value"] = f"{command_units_per_rev:.3f}"



    



    except ParseError as exc:
        print(f"Parse error: {exc}")
        return None

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
