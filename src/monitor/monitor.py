#!/usr/bin/env python3

import argparse
import logging
import sys
import os

# Add the parent directory to the path so we can import monitor modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from monitor.config import MonitorConfig
from monitor.gui import SimpleMonitorGUI as MonitorGUI
from monitor.serial_reader import list_serial_ports
import json


def main():
    """Main entry point for monitor command"""
    parser = argparse.ArgumentParser(
        description="MCU Data Monitor - Real-time GUI for comma-separated MCU data",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Configuration options
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "-c", "--config",
        help="Configuration file path (JSON format). Required to run the monitor."
    )
    config_group.add_argument(
        "--create-config",
        action="store_true",
        help="Print an example configuration to stdout and exit"
    )
    
    # Information options
    info_group = parser.add_argument_group("Information")
    info_group.add_argument(
        "--list",
        action="store_true",
        help="List available serial ports and exit"
    )
    info_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(message)s')
    
    # Handle --list command
    if args.list:
        print("Available serial ports:")
        print("-" * 60)
        ports = list_serial_ports()
        if ports:
            for port, desc, hwid in ports:
                print(f"  {port:<20} {desc}")
                if args.verbose and hwid:
                    print(f"    Hardware ID: {hwid}")
            print("-" * 60)
            print(f"Found {len(ports)} port(s)")
        else:
            print("  No serial ports found")
            print("-" * 60)
        return
    
    # Handle information commands (create-config)
    if args.create_config:
        # Create example config and print to stdout
        config = MonitorConfig()
        example_config = config.create_example_config()
        print(json.dumps(example_config, indent=2))
        return
    
    # Load configuration
    if not args.config:
        # No config file specified - show help and exit
        parser.print_help()
        
        print("\nERROR: Configuration file is required")
        sys.exit(1)
    
    try:
        if not os.path.exists(args.config):
            print(f"Configuration file not found: {args.config}")
            print("Use --create-config to generate an example: monitor --create-config > config.json")
            sys.exit(1)
        
        config = MonitorConfig(config_file=args.config)
        print(f"Loaded configuration from: {args.config}")
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Create and run GUI
    try:
        ports = config.get_ports()
        if not ports:
            print("Warning: No ports configured in configuration file")
            print("Add port configurations to your config file. Example:")
            print("""
{
  "ports": {
    "/dev/ttyUSB0": {
      "baudrate": 115200,
      "0": {"label": "Field 1", "type": "int"},
      "1": {"label": "Field 2", "type": "float"}
    }
  }
}
""")
        
        gui = MonitorGUI(config)
        
        print(f"Starting monitor with {len(ports)} port(s): {', '.join(ports)}")
        for port in ports:
            baudrate = config.get_port_baudrate(port)
            print(f"  {port}: {baudrate} baud")
        
        # Auto-connect after GUI is ready
        gui.root.after(100, gui.connect)
        
        gui.run()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logging.error(f"Application error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()