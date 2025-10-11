#!/usr/bin/env python3

import argparse
import logging
import sys
import os

from okimotus.monitor.config import MonitorConfig, create_default_config_file
from okimotus.monitor.gui import MonitorGUI
from okimotus.monitor.serial_reader import list_serial_ports
from okimotus.utils import pr_red, pr_yellow, pr_green


def ask_for_port():
    """Interactive port selection"""
    ports = list_serial_ports()
    
    if not ports:
        print("No serial ports found")
        return None
    
    print("Available ports:")
    for i, (port, desc, hwid) in enumerate(ports, 1):
        print(f"  {i}: {port} - {desc}")
    
    while True:
        try:
            choice = input("Enter port number or full port name: ").strip()
            
            # Try as number first
            try:
                index = int(choice) - 1
                if 0 <= index < len(ports):
                    return ports[index][0]
                else:
                    print("Invalid port number")
                    continue
            except ValueError:
                pass
            
            # Try as port name
            for port, _, _ in ports:
                if port == choice:
                    return port
            
            print("Port not found, try again")
            
        except KeyboardInterrupt:
            print("\nCancelled")
            return None


def main():
    """Main entry point for monitor command"""
    parser = argparse.ArgumentParser(
        description="MCU Data Monitor - Real-time GUI for comma-separated MCU data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  monitor --create-config               # Create example configuration file
  monitor -c config.json -p /dev/ttyUSB0  # Use config file with specific port
  monitor -c config.json -b 9600        # Use config file with specific baudrate
  monitor --list-ports                  # List available serial ports

Configuration File Required:
  A JSON configuration file is REQUIRED to define field mappings.
  Use --create-config to generate an example file.
  
  {
    "title": "My MCU Monitor",
    "refresh_rate": 100,
    "window": {"width": 800, "height": 600},
    "fields": {
      "0": {"label": "Encoder 1", "type": "int", "format": "{:,}", "unit": "counts"},
      "1": {"label": "Encoder 2", "type": "int", "format": "{:,}", "unit": "counts"},
      "2": "Simple Label",
      "3": {"label": "Temperature", "type": "float", "format": "{:.2f}", "unit": "°C"}
    }
  }

MCU Data Format:
  Send comma-separated values from your MCU:
  "1234,5678,active,temp_sensor,42,98765"
  
  Each position (0,1,2...) maps to a configured field.
        """
    )
    
    # Connection options
    connection_group = parser.add_argument_group("Connection")
    connection_group.add_argument(
        "-p", "--port",
        help="Serial port name (e.g., /dev/ttyUSB0, COM3). If not specified, will prompt for selection."
    )
    connection_group.add_argument(
        "-b", "--baudrate",
        type=int,
        default=115200,
        help="Serial baudrate (default: 115200)"
    )
    connection_group.add_argument(
        "--ask-port",
        action="store_true",
        help="Interactively ask for port selection"
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
        "--list-ports",
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
    
    # Handle information commands
    if args.list_ports:
        ports = list_serial_ports()
        if ports:
            print("Available serial ports:")
            for port, desc, hwid in ports:
                print(f"  {port:<20} {desc}")
        else:
            print("No serial ports found")
        return
    
    if args.create_config:
        config_file = "monitor_config.json"
        try:
            create_default_config_file(config_file)
            print(f"Created example configuration file: {config_file}")
            print(f"Edit this file to customize your field mappings, then run:")
            print(f"  monitor -c {config_file}")
        except Exception as e:
            print(pr_red(f"Failed to create configuration file: {e}"))
            sys.exit(1)
        return
    
    # Load configuration
    try:
        if args.config:
            if not os.path.exists(args.config):
                print(pr_red(f"Configuration file not found: {args.config}"))
                print(pr_yellow("Use --create-config to create an example configuration file."))
                sys.exit(1)
            
            config = MonitorConfig(config_file=args.config)
            print(pr_green(f"Loaded configuration from: {args.config}"))
        else:
            # Use demo configuration
            config = MonitorConfig()
            demo_config = config.create_example_config()
            config.load_from_dict(demo_config)
            print(pr_green("Using demo configuration with transformations"))
    except Exception as e:
        print(pr_red(f"Failed to load configuration: {e}"))
        sys.exit(1)
    
    # Determine serial port
    port = None
    if args.ask_port:
        port = ask_for_port()
        if not port:
            print("No port selected")
            sys.exit(1)
    elif args.port:
        port = args.port
    else:
        # Try to auto-select or ask
        ports = list_serial_ports()
        if len(ports) == 1:
            port = ports[0][0]
            print(pr_green(f"Auto-selected port: {port}"))
        elif len(ports) > 1:
            print(pr_yellow("Multiple ports available. Please specify one with -p <port> or use --ask-port"))
            print("Available ports:")
            for p, desc, _ in ports:
                print(f"  {p} - {desc}")
            sys.exit(1)
        else:
            print(pr_yellow("No serial port specified. Running in demo mode (no data will be received)."))
            print(pr_yellow("Use -p <port> to connect to a serial device, or --list-ports to see available ports."))
    
    # Create and run GUI
    try:
        gui = MonitorGUI(config, port, args.baudrate)
        
        # Auto-connect if port was specified
        if port:
            print(pr_green(f"Starting monitor on {port} at {args.baudrate} baud"))
            gui.root.after(100, gui.connect)  # Connect after GUI is ready
        
        gui.run()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logging.error(pr_red(f"Application error: {e}"))
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()