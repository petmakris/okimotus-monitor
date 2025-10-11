#!/usr/bin/env python3

import argparse
import logging
import sys
import os

# Add the parent directory to the path so we can import monitor modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from monitor.config import MonitorConfig, create_default_config_file
from monitor.gui import SimpleMonitorGUI as MonitorGUI
from monitor.serial_reader import list_serial_ports

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
            
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled or no interactive terminal available")
            return None
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
            print(f"Failed to create configuration file: {e}")
            sys.exit(1)
        return
    
    # Load configuration
    try:
        if args.config:
            if not os.path.exists(args.config):
                print(f"Configuration file not found: {args.config}")
                print("Use --create-config to create an example configuration file.")
                sys.exit(1)
            
            config = MonitorConfig(config_file=args.config)
            print(f"Loaded configuration from: {args.config}")
        else:
            # Use demo configuration
            config = MonitorConfig()
            demo_config = config.create_example_config()
            config.load_from_dict(demo_config)
            print("Using demo configuration with transformations")
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Determine serial port
    port = None
    if args.ask_port:
        port = ask_for_port()
        if not port:
            print("No port selected, you can select one from the GUI")
    elif args.port:
        port = args.port
    else:
        # Try to auto-select or show available ports
        ports = list_serial_ports()
        if len(ports) == 1:
            port = ports[0][0]
            print(f"Auto-selected port: {port}")
        elif len(ports) > 1:
            print("Multiple ports available. You can select one from the GUI or specify with -p <port>")
            print("Available ports:")
            for p, desc, _ in ports:
                print(f"  {p} - {desc}")
        else:
            print("No serial ports found. You can still use the GUI and connect later.")
    
    # Create and run GUI (always create it, even without a port)
    try:
        gui = MonitorGUI(config, port, args.baudrate)
        
        # Auto-connect if port was specified
        if port:
            print(f"Starting monitor on {port} at {args.baudrate} baud")
            gui.root.after(100, gui.connect)  # Connect after GUI is ready
        else:
            print("GUI started. Use 'Select Port' button to choose a serial port.")
        
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