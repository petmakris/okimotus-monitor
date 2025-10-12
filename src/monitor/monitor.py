#!/usr/bin/env python3

import argparse
import logging
import sys
import os

# Add the parent directory to the path so we can import monitor modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from monitor.config import MonitorConfig, create_default_config_file
from monitor.gui import SimpleMonitorGUI as MonitorGUI


def main():
    """Main entry point for monitor command"""
    parser = argparse.ArgumentParser(
        description="MCU Data Monitor - Real-time GUI for comma-separated MCU data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  monitor --create-config               # Create example configuration file
  monitor -c config.json                # Use config file
  monitor -c config.json -b 9600        # Use config file with specific baudrate

Configuration File Required:
  A JSON configuration file is REQUIRED to define field mappings and serial ports.
  Use --create-config to generate an example file.
  
  {
    "title": "My MCU Monitor",
    "refresh_rate": 100,
    "window": {"width": 800, "height": 600},
    "ports": {
      "/dev/ttyUSB0": {
        "0": {"label": "Encoder 1", "type": "int", "format": "{:,}", "unit": "counts"},
        "1": {"label": "Encoder 2", "type": "int", "format": "{:,}", "unit": "counts"}
      },
      "/dev/ttyUSB1": {
        "0": {"label": "Temperature", "type": "float", "format": "{:.2f}", "unit": "°C"}
      }
    }
  }

MCU Data Format:
  Send comma-separated values from your MCU:
  "1234,5678,active,temp_sensor,42,98765"
  
  Each position (0,1,2...) maps to a configured field for that port.
        """
    )
    
    # Connection options
    connection_group = parser.add_argument_group("Connection")
    connection_group.add_argument(
        "-b", "--baudrate",
        type=int,
        default=115200,
        help="Serial baudrate (default: 115200)"
    )
    
    # Configuration options
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "-c", "--config",
        help="Configuration file path (JSON format). If not specified, uses demo configuration."
    )
    config_group.add_argument(
        "--create-config",
        action="store_true",
        help="Create an example configuration file and exit"
    )
    
    # Information options
    info_group = parser.add_argument_group("Information")
    info_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(message)s')
    
    # Handle information commands (create-config)
    if args.create_config:
        config_file = "monitor_config.json"
        try:
            create_default_config_file(config_file)
            print(f"Created example configuration file: {config_file}")
            print(f"Edit this file to customize your field mappings, then run:")
            print(f"  monitor -c {config_file}")
        except Exception as e:
            print(f"Failed to create configuration file: {e}")
            sys.exit(1)
        return
    
    # Load configuration
    if not args.config:
        # No config file specified - show help and exit
        parser.print_help()
        print("\n" + "="*60)
        print("ERROR: Configuration file is required")
        print("="*60)
        print("\nQuick start:")
        print("  1. Create a config file:  monitor --create-config")
        print("  2. Edit the config file:  nano monitor_config.json")
        print("  3. Run the monitor:       monitor -c monitor_config.json")
        sys.exit(1)
    
    try:
        if not os.path.exists(args.config):
            print(f"Configuration file not found: {args.config}")
            print("Use --create-config to create an example configuration file.")
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
      "0": {"label": "Field 1", "type": "int"},
      "1": {"label": "Field 2", "type": "float"}
    }
  }
}
""")
        
        gui = MonitorGUI(config, args.baudrate)
        
        print(f"Starting monitor with {len(ports)} port(s): {', '.join(ports)}")
        print(f"Baudrate: {args.baudrate}")
        
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