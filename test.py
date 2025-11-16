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


def entry(label: str, value: str, unit: str = "") -> str:
    return { "label": label, "value": value, "unit": unit }


def entryf(label: str, value: float, unit: str = "") -> str:
    return { "label": label, "value": f"{value:.3f}", "unit": unit }


def render(lines: Mapping[str, Optional[SerialLine]]) -> Optional[Iterable[Mapping[str, object]]]:
    global _last_parse_error

    encoder = lines.get("encoder")
    axis = lines.get("axis")

    
    rows = []
    try:
        # Axis line format:
        #
        # 2725,  -- time
        # 0,     -- units (0=mm,1=in,2=deg)
        # 2700,  -- steps
        # 8.44,  -- current position in units
        # 5.00   -- units per revolution

        if not encoder and not axis:
            raise ParseError("No data received from either axis or encoder")

        axis_time              = to_int(axis, index=0)
        axis_units             = to_int(axis, 1)
        axis_steps             = to_float(axis, index=2)
        axis_curr_pos_in_units = to_float(axis, index=3)
        axis_units_per_rev     = to_float(axis, index=4)

        rows.append(entry("Axis Time", str(axis_time), "s"))
        rows.append(entry("Axis Units", parse_units(axis_units)))

        rows.append(entryf("Axis Steps", axis_steps, "steps"))
        rows.append(entryf("Axis Position in Units", axis_curr_pos_in_units, "units"))
        rows.append(entryf("Axis Units per Revolution", axis_units_per_rev, "units/rev"))

        # Encoder line format:
        #
        # 2725,  -- time
        # 1600   -- counts of encoder 1
        # 1600   -- counts of encoder 2 (not really used in this demo)

        enc_time   = to_int(encoder, index=0)
        enc_counts = to_float(encoder, index=1)
        enc_revs   = enc_counts / 1600.0

        rows.append(entry("Encoder Time", str(enc_time), "s"))
        rows.append(entry("Encoder Counts", enc_counts, "counts"))
        rows.append(entryf("Encoder Revolutions", enc_revs, "rev"))

        # I want to show encoder position in units as well, so I compute it here:
        # I have to take into account the units!
        if axis_units_per_rev != 0:
            enc_pos_in_units = enc_revs * axis_units_per_rev
            rows.append(entryf("Encoder Position in Units", enc_pos_in_units, "units"))
    


    except ParseError as exc:
        print(f"Parse error: {exc}")
        return None

    return rows


if __name__ == '__main__':
    run(
        {
            "encoder": {"device": "/dev/ttyUSB0", "baudrate": 115200},
            "axis": {"device": "/dev/ttyUSB1", "baudrate": 115200},
        },
        render=render,
        poll_interval=0.5,
    )
