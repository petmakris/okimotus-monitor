#!/usr/bin/env python3

import yaml
import logging
import os
import math
from typing import Dict, List, Any, Optional



class MonitorConfig:
    """Configuration parser for MCU data monitoring"""
    
    def __init__(self, config_file: str = None, config_dict: dict = None):
        self.port_fields: Dict[str, List[Dict[str, Any]]] = {}  # port -> list of field configs
        self.port_settings: Dict[str, Dict[str, Any]] = {}  # port -> settings (baudrate, etc.)
        self.fields_by_index: Dict[str, Dict[int, List[Dict[str, Any]]]] = {}  # port -> index -> [fields]
        self.field_lookup: Dict[str, Dict[str, Any]] = {}  # id -> field config
        self._field_counter: int = 0
        self.title: str = "MCU Monitor"
        self.window_size: tuple = (800, 600)
        self.python_builtins = {
            'abs': abs,
            'min': min,
            'max': max,
            'pow': pow,
            'round': round,
            'sum': sum
        }
        
        if config_file:
            self.load_from_file(config_file)
        elif config_dict:
            self.load_from_dict(config_dict)
    
    def load_from_file(self, config_file: str):
        """Load configuration from YAML file"""
        try:
            # Detect file type by extension
            _, ext = os.path.splitext(config_file)
            ext = ext.lower()
            if ext not in ['.yaml', '.yml']:
                raise ValueError("Only YAML configuration files (.yaml or .yml) are supported")

            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
                self.load_from_dict(config_data)
        except FileNotFoundError:
            logging.error(f"Configuration file not found: {config_file}")
            raise
        except yaml.YAMLError as e:
            logging.error(f"Invalid configuration file format: {e}")
            raise
    
    def load_from_dict(self, config_data: dict):
        """Load configuration from dictionary"""
        self._reset_config_state()
        # Extract global settings
        self.title = config_data.get('title', self.title)
        window_config = config_data.get('window', {})
        self.window_size = (
            window_config.get('width', 800),
            window_config.get('height', 600)
        )
        
        # Parse ports configuration (new multi-port format)
        if 'ports' in config_data:
            ports_config = config_data.get('ports', {})
            for port_name, port_data in ports_config.items():
                if port_data is None:
                    continue
                
                self.port_fields[port_name] = []
                self.fields_by_index[port_name] = {}
                
                # Extract port settings (baudrate, etc.)
                self.port_settings[port_name] = {
                    'baudrate': port_data.get('baudrate', 115200)  # Default to 115200 if not specified
                }
                
                values_config = port_data.get('values')
                if isinstance(values_config, list):
                    self._parse_values_block(port_name, values_config)
                else:
                    # Legacy format: position -> config entries
                    self._parse_legacy_fields(port_name, port_data)

    def _reset_config_state(self):
        """Reset per-load state before parsing."""
        self.port_fields = {}
        self.port_settings = {}
        self.fields_by_index = {}
        self.field_lookup = {}
        self._field_counter = 0
    
    def _parse_values_block(self, port_name: str, values_block: List[Any]):
        """Parse the new list-based field definitions."""
        for idx, entry in enumerate(values_block):
            if entry is None:
                continue
            if not isinstance(entry, dict):
                logging.warning(f"Ignoring invalid entry at values[{idx}] for {port_name}: expected mapping")
                continue
            
            if 'index' not in entry:
                logging.warning(f"Ignoring entry without 'index' for {port_name}: {entry}")
                continue
            
            try:
                position = self._parse_position_value(entry.get('index'))
            except (ValueError, TypeError) as e:
                logging.warning(f"Invalid index '{entry.get('index')}' for port {port_name}: {e}")
                continue
            
            field_entry = self._build_field_entry(port_name, position, entry)
            self._register_field(port_name, field_entry)
    
    def _parse_legacy_fields(self, port_name: str, port_data: Dict[str, Any]):
        """Parse legacy map-based field definitions (position -> config)."""
        for position_key, field_config in port_data.items():
            if position_key in ('baudrate', 'values'):
                continue
            
            try:
                position = self._parse_position_value(position_key)
            except (ValueError, TypeError) as e:
                logging.warning(f"Invalid field position '{position_key}' for port {port_name}: {e}")
                continue
            
            field_entry = self._build_field_entry(port_name, position, field_config)
            self._register_field(port_name, field_entry)
    
    def _parse_position_value(self, value: Any) -> int:
        """Convert YAML key/index to integer position."""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("empty string")
            return int(value, 10)
        raise TypeError(f"Unsupported index type: {type(value)}")
    
    def _build_field_entry(self, port_name: str, index: int, raw_config: Any) -> Dict[str, Any]:
        """Normalize raw field configuration to internal format."""
        if isinstance(raw_config, str):
            normalized = {'label': raw_config}
        elif isinstance(raw_config, dict):
            normalized = dict(raw_config)
        elif raw_config is None:
            normalized = {}
        else:
            logging.warning(f"Unsupported field configuration for port {port_name}, index {index}: {raw_config}")
            normalized = {}
        
        format_str = normalized.get('format', '{}')
        if not isinstance(format_str, str):
            format_str = str(format_str)
        
        enabled_value = self._get_case_insensitive(normalized, 'enabled')
        disabled_value = self._get_case_insensitive(normalized, 'disabled')
        if enabled_value is not None:
            enabled = self._parse_bool(enabled_value, default=True)
        elif disabled_value is not None:
            enabled = not self._parse_bool(disabled_value, default=False)
        else:
            enabled = True
        
        field_entry = {
            'id': f"{port_name}#{self._field_counter}",
            'port': port_name,
            'index': index,
            'label': normalized.get('label', f'Field {index}'),
            'type': normalized.get('type', 'string'),
            'format': format_str,
            'unit': normalized.get('unit', ''),
            'color': normalized.get('color', 'black'),
            'min': normalized.get('min'),
            'max': normalized.get('max'),
            'python': normalized.get('python'),
            'enabled': enabled
        }
        self._field_counter += 1
        return field_entry
    
    def _register_field(self, port_name: str, field_entry: Dict[str, Any]):
        """Register a parsed field entry into lookup tables."""
        self.port_fields.setdefault(port_name, []).append(field_entry)
        self.field_lookup[field_entry['id']] = field_entry
        
        if field_entry.get('enabled', True):
            index = field_entry['index']
            port_index_map = self.fields_by_index.setdefault(port_name, {})
            port_index_map.setdefault(index, []).append(field_entry)
    
    @staticmethod
    def _get_case_insensitive(data: Dict[str, Any], key: str) -> Any:
        """Fetch dictionary value regardless of key casing."""
        if not isinstance(data, dict):
            return None
        key_lower = key.lower()
        for existing_key, value in data.items():
            if isinstance(existing_key, str) and existing_key.lower() == key_lower:
                return value
        return None
    
    @staticmethod
    def _parse_bool(value: Any, default: bool = True) -> bool:
        """Parse boolean-like values from YAML."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ('true', '1', 'yes', 'on'):
                return True
            if lowered in ('false', '0', 'no', 'off'):
                return False
            return default
        return bool(value)
    
    def get_ports(self) -> List[str]:
        """Get all configured port names"""
        return list(self.port_fields.keys())
    
    def get_port_baudrate(self, port: str) -> int:
        """Get baudrate for a specific port"""
        if port in self.port_settings:
            return self.port_settings[port].get('baudrate', 115200)
        return 115200  # Default fallback
    
    def get_field_config(self, port: str, position: Optional[int] = None, field_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get field configuration by ID or by source position (first enabled match)."""
        if field_id:
            return self.field_lookup.get(field_id)
        
        if position is None or port not in self.port_fields:
            return None
        
        for field in self.port_fields[port]:
            if field.get('index') == position and field.get('enabled', True):
                return field
        return None
    
    def get_fields_for_port(self, port: str, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """Return list of field configurations for a port."""
        fields = self.port_fields.get(port, [])
        if include_disabled:
            return list(fields)
        return [field for field in fields if field.get('enabled', True)]
    
    def get_fields_for_index(self, port: str, index: int, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """Return all fields sourcing from the same index."""
        if include_disabled:
            return [
                field for field in self.port_fields.get(port, [])
                if field.get('index') == index
            ]
        return list(self.fields_by_index.get(port, {}).get(index, []))
    
    def get_all_positions(self, port: str) -> List[int]:
        """Get all configured field source positions for a specific port"""
        if port not in self.port_fields:
            return []
        positions = {
            field.get('index')
            for field in self.port_fields[port]
            if field.get('enabled', True)
        }
        return sorted(positions)
    
    def format_value(
        self,
        field_or_port: Any,
        position_or_raw: Any,
        raw_value: Optional[str] = None,
        line_data: Optional[Dict[int, Any]] = None
    ) -> str:
        """
        Format a raw value according to field configuration (with optional python conversion).
        Can be called as format_value(field_config, raw_value) or format_value(port, position, raw_value).
        """
        if isinstance(field_or_port, dict):
            field_config = field_or_port
            raw_input = position_or_raw
        else:
            field_config = self.get_field_config(field_or_port, position_or_raw)
            raw_input = raw_value
        
        if not field_config:
            return raw_input if raw_input is not None else '---'
        
        return self._format_with_field(field_config, raw_input, line_data)

    def _format_with_field(
        self,
        field_config: Dict[str, Any],
        raw_value: str,
        line_data: Optional[Dict[int, Any]] = None
    ) -> str:
        """Internal helper that applies typing, python conversion, and formatting."""
        if raw_value is None:
            return '---'
        
        cleaned_value = raw_value.strip()
        if not cleaned_value or '\x00' in cleaned_value:
            return '---'
        
        try:
            field_type = field_config.get('type', 'string')
            if field_type == 'int':
                value = int(cleaned_value)
            elif field_type == 'float':
                value = float(cleaned_value)
            else:
                value = cleaned_value
            
            converted_value = self.apply_python_conversion(
                field_config,
                value,
                cleaned_value,
                line_data=line_data
            )
            formatted = field_config.get('format', '{}').format(converted_value)
            
            unit = field_config.get('unit', '')
            if unit:
                formatted += f" {unit}"
            
            return formatted
        except (ValueError, TypeError) as e:
            label = field_config.get('label', 'field')
            logging.warning(f"Failed to format value '{raw_value}' for {label}: {e}")
            return '---'
    def apply_python_conversion(
        self,
        field_config: Dict[str, Any],
        value: Any,
        raw_value: str,
        line_data: Optional[Dict[int, Any]] = None
    ) -> Any:
        """Run optional python snippet defined in the configuration"""
        python_code = field_config.get('python')
        if not python_code:
            return value

        safe_globals = {
            '__builtins__': dict(self.python_builtins),
            'math': math
        }
        raw_line = dict(line_data) if line_data else {}
        converted_line = self._convert_line_values(raw_line)
        local_vars = {
            'value': value,
            'raw_value': raw_value,
            'field': field_config,
            'line': raw_line,
            'line_values': converted_line
        }
        label = field_config.get('label', 'field')

        try:
            compiled = compile(python_code, f"<python:{label}>", 'eval')
            return eval(compiled, safe_globals, local_vars)
        except SyntaxError:
            try:
                compiled = compile(python_code, f"<python:{label}>", 'exec')
                exec(compiled, safe_globals, local_vars)
                if 'result' in local_vars:
                    return local_vars['result']
                return local_vars.get('value', value)
            except Exception as error:
                logging.warning(f"Python conversion failed for {label}: {error}")
                return value
        except Exception as error:
            logging.warning(f"Python conversion failed for {label}: {error}")
            return value

    @staticmethod
    def _convert_line_values(line_data: Dict[int, Any]) -> Dict[int, Any]:
        """Attempt to convert raw line values to numbers when possible."""
        converted: Dict[int, Any] = {}
        for index, raw in line_data.items():
            converted[index] = MonitorConfig._auto_convert_scalar(raw)
        return converted

    @staticmethod
    def _auto_convert_scalar(raw: Any) -> Any:
        """Best-effort conversion of a scalar value to int/float when reasonable."""
        if isinstance(raw, (int, float)) or raw is None:
            return raw
        value_str = str(raw).strip()
        if value_str == '':
            return ''
        try:
            return int(value_str, 10)
        except (ValueError, TypeError):
            pass
        try:
            return float(value_str)
        except (ValueError, TypeError):
            return raw
    
    def create_example_config(self) -> dict:
        """Create an example configuration dictionary"""
        return {
            "title": "Phase Tracker",
            "window": {
                "width": 1000,
                "height": 600
            },
            "ports": {
                "/dev/ttyUSB0": {
                    "baudrate": 115200,
                    "values": [
                        {
                            "label": "Time (ms)",
                            "index": 0,
                            "type": "int",
                            "format": "{:.0f}",
                            "unit": "ms",
                            "color": "blue"
                        },
                        {
                            "label": "Time (s)",
                            "index": 0,
                            "type": "int",
                            "format": "{:.3f}",
                            "unit": "s",
                            "color": "blue",
                            "python": "value / 1000"
                        },
                        {
                            "label": "Encoder 1 (deg)",
                            "index": 1,
                            "type": "int",
                            "format": "{:.1f}",
                            "unit": "°",
                            "color": "green",
                            "python": "(value / 1600) * 360"
                        },
                        {
                            "label": "Encoder 1 (mm)",
                            "index": 1,
                            "type": "int",
                            "format": "{:.2f}",
                            "unit": "mm",
                            "color": "orange",
                            "python": "(value / 1600) * 5",
                            "enabled": False
                        },
                        {
                            "label": "Encoder 2",
                            "index": 2,
                            "type": "int",
                            "format": "{:.3f}",
                            "unit": "rev",
                            "color": "red",
                            "python": "value / 4096"
                        }
                    ]
                }
            }
        }


def create_default_config_file(filename: str = "monitor_config.yaml"):
    """Create a default configuration file"""
    config = MonitorConfig()
    example_config = config.create_example_config()
    
    try:
        with open(filename, 'w') as f:
            yaml.safe_dump(example_config, f, sort_keys=False)
        logging.info(f"Created example configuration file: {filename}")
    except IOError as e:
        logging.error(f"Failed to create configuration file: {e}")
        raise


if __name__ == "__main__":
    # Create example config for testing
    create_default_config_file()
