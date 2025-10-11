#!/usr/bin/env python3

import json
import logging
from typing import Dict, List, Any, Optional



class MonitorConfig:
    """Configuration parser for MCU data monitoring"""
    
    def __init__(self, config_file: str = None, config_dict: dict = None):
        self.fields: Dict[int, Dict[str, Any]] = {}
        self.title: str = "MCU Monitor"
        self.refresh_rate: int = 100  # milliseconds
        self.window_size: tuple = (800, 600)
        
        if config_file:
            self.load_from_file(config_file)
        elif config_dict:
            self.load_from_dict(config_dict)
    
    def load_from_file(self, config_file: str):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                self.load_from_dict(config_data)
        except FileNotFoundError:
            logging.error(f"Configuration file not found: {config_file}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in configuration file: {e}")
            raise
    
    def load_from_dict(self, config_data: dict):
        """Load configuration from dictionary"""
        # Extract global settings
        self.title = config_data.get('title', self.title)
        self.refresh_rate = config_data.get('refresh_rate', self.refresh_rate)
        window_config = config_data.get('window', {})
        self.window_size = (
            window_config.get('width', 800),
            window_config.get('height', 600)
        )
        
        # Parse field configurations
        fields_config = config_data.get('fields', {})
        for position_str, field_config in fields_config.items():
            try:
                position = int(position_str)
                
                # Handle both simple string labels and complex field configs
                if isinstance(field_config, str):
                    self.fields[position] = {
                        'label': field_config,
                        'type': 'string',
                        'format': '{}',
                        'unit': ''
                    }
                else:
                    self.fields[position] = {
                        'label': field_config.get('label', f'Field {position}'),
                        'type': field_config.get('type', 'string'),
                        'format': field_config.get('format', '{}'),
                        'unit': field_config.get('unit', ''),
                        'color': field_config.get('color', 'black'),
                        'min': field_config.get('min'),
                        'max': field_config.get('max'),
                        'transformations': field_config.get('transformations', [])
                    }
            except (ValueError, TypeError) as e:
                logging.warning(f"Invalid field position '{position_str}': {e}")
    
    def get_field_config(self, position: int) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific field position"""
        return self.fields.get(position)
    
    def get_all_positions(self) -> List[int]:
        """Get all configured field positions sorted"""
        return sorted(self.fields.keys())
    
    def format_value(self, position: int, raw_value: str) -> str:
        """Format a raw value according to field configuration"""
        field_config = self.get_field_config(position)
        if not field_config:
            return raw_value
        
        try:
            # Type conversion
            field_type = field_config['type']
            if field_type == 'int':
                value = int(raw_value)
            elif field_type == 'float':
                value = float(raw_value)
            else:
                value = raw_value
            
            # Apply format string
            formatted = field_config['format'].format(value)
            
            # Add unit if specified
            unit = field_config.get('unit', '')
            if unit:
                formatted += f" {unit}"
            
            return formatted
        except (ValueError, TypeError) as e:
            logging.warning(f"Failed to format value '{raw_value}' for position {position}: {e}")
            return raw_value
    
    def apply_transformation(self, value, transformation: dict) -> float:
        """Apply a single transformation to a numeric value"""
        operation = transformation.get('operation', 'multiply')
        transform_value = transformation.get('value', 1)
        
        if operation == 'multiply':
            return value * transform_value
        elif operation == 'divide':
            if transform_value == 0:
                logging.warning(f"Division by zero in transformation")
                return 0
            return value / transform_value
        elif operation == 'add':
            return value + transform_value
        elif operation == 'subtract':
            return value - transform_value
        elif operation == 'power':
            return value ** transform_value
        else:
            logging.warning(f"Unknown transformation operation: {operation}")
            return value
    
    def format_transformation(self, transformation: dict, transformed_value: float) -> str:
        """Format a transformed value according to transformation configuration"""
        format_str = transformation.get('format', '{:.3f}')
        unit = transformation.get('unit', '')
        
        try:
            formatted = format_str.format(transformed_value)
            if unit:
                formatted += f" {unit}"
            return formatted
        except (ValueError, TypeError) as e:
            logging.warning(f"Failed to format transformed value: {e}")
            return str(transformed_value)
    
    def get_transformed_values(self, position: int, raw_value: str) -> List[Dict[str, str]]:
        """Get all transformed values for a field position"""
        field_config = self.get_field_config(position)
        if not field_config:
            return []
        
        transformations = field_config.get('transformations', [])
        if not transformations:
            return []
        
        try:
            # Convert raw value to numeric
            field_type = field_config['type']
            if field_type == 'int':
                numeric_value = int(raw_value)
            elif field_type == 'float':
                numeric_value = float(raw_value)
            else:
                return []  # Can't transform non-numeric values
            
            results = []
            for transformation in transformations:
                try:
                    transformed_value = self.apply_transformation(numeric_value, transformation)
                    formatted_value = self.format_transformation(transformation, transformed_value)
                    results.append({
                        'label': transformation.get('label', 'Transformed'),
                        'value': formatted_value,
                        'raw_value': transformed_value
                    })
                except Exception as e:
                    logging.warning(f"Failed to apply transformation: {e}")
                    results.append({
                        'label': transformation.get('label', 'Error'),
                        'value': '---',
                        'raw_value': 0
                    })
            
            return results
        except (ValueError, TypeError) as e:
            logging.warning(f"Failed to convert value for transformation: {e}")
            return []
    
    def create_example_config(self) -> dict:
        """Create an example configuration dictionary"""
        return {
            "title": "Phase Tracker",
            "refresh_rate": 100,
            "window": {
                "width": 1000,
                "height": 600
            },
            "fields": {
                "0": {
                    "label": "Time",
                    "type": "int",
                    "format": "{:,}",
                    "unit": "counts",
                    "color": "blue",
                    "transformations": [
                        {
                            "label": "Seconds",
                            "operation": "divide",
                            "value": 1000,
                            "format": "{:.3f}",
                            "unit": "s"
                        }
                    ]
                },
                "1": {
                    "label": "Encoder 1",
                    "type": "int",
                    "format": "{:,}",
                    "unit": "counts",
                    "color": "green",
                    "transformations": [
                        {
                            "label": "Rotations",
                            "operation": "divide",
                            "value": 1600,
                            "format": "{:.3f}",
                            "unit": "rev"
                        },
                        {
                            "label": "Degrees",
                            "operation": "multiply",
                            "value": 0.225,
                            "format": "{:.1f}",
                            "unit": "°"
                        }
                    ]
                },
                "2": {
                    "label": "Encoder 2",
                    "type": "int",
                    "format": "{:,}",
                    "unit": "counts",
                    "color": "red",
                    "transformations": [
                        {
                            "label": "Rotations",
                            "operation": "divide",
                            "value": 4096,
                            "format": "{:.3f}",
                            "unit": "rev"
                        }
                    ]
                }
            }
        }


def create_default_config_file(filename: str = "monitor_config.json"):
    """Create a default configuration file"""
    config = MonitorConfig()
    example_config = config.create_example_config()
    
    try:
        with open(filename, 'w') as f:
            json.dump(example_config, f, indent=2)
        logging.info(f"Created example configuration file: {filename}")
    except IOError as e:
        logging.error(f"Failed to create configuration file: {e}")
        raise


if __name__ == "__main__":
    # Create example config for testing
    create_default_config_file()