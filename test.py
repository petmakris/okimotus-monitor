#!/usr/bin/env python3
"""Axis monitor demo translated from the legacy YAML configuration."""

from __future__ import annotations

from typing import Optional

from monitor import get_port, out, shutdown


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
    if (value == 1): 
        return "mm"
    elif (value == 2):
        return "in"
    elif (value == 3):
        return "deg"
    else:
        return "--"



def main():
    encoder_port = get_port('/dev/ttyUSB0', baudrate=115200)
    command_port = get_port('/dev/ttyUSB1', baudrate=115200)

    try:
        while True:
            rows = [
                {"label": "Motor Revs (Encoder)", "value": "--"},
                {"label": "Radial Degrees (Encoder)", "value": "--"},

                {"label": "Units", "value": "--"},
                {"label": "Radial Degrees (Cmd)", "value": "--"},
                # {"label": "Units / Motor Rev", "value": "--"},
            ]

            encoder_line = encoder_port.readline()
            command_line = command_port.readline()

            if encoder_line:
                encoder_counts = to_float(encoder_line, 1)
                encoder_motor_revs = encoder_counts / 1600.0
                encoder_radial_degrees = (encoder_counts / 1600.0) * 10.0

                rows[0] = {"label": "Motor Revs (Encoder)", "value": f"{encoder_motor_revs:.3f} rev"}
                rows[1] = {"label": "Radial Degrees (Encoder)", "value": f"{encoder_radial_degrees:.3f} deg"}
            if command_line:
                command_counts = to_float(command_line, index=2)
                command_dynamic_scale = to_float(command_line, index=5, default=10.0)
                radial_degrees = (command_counts / 1600.0) * command_dynamic_scale

                rows[2] = {"label": "Units", "value": parse_units(to_int(command_line, 1))}
                rows[3] = {"label": "Radial Degrees (Cmd)", "value": f"{radial_degrees:.3f} deg"}
            
            out(rows)
            # rows[4] = {"label": "Units / Motor Rev", "value": f"{units_per_rev:.3f}"}


            # out(rows)

    finally:
        shutdown()
        encoder_port.close()
        command_port.close()


if __name__ == '__main__':
    main()
