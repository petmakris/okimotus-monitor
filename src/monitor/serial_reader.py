#!/usr/bin/env python3

import logging
import threading
import time
from typing import List, Dict, Any, Optional, Callable
from queue import Queue, Empty

import serial
from serial.tools.list_ports import comports

from okimotus.utils import pr_red, pr_yellow, pr_green


class SerialDataParser:
    """Parser for comma-separated MCU data"""
    
    def __init__(self, delimiter: str = ',', line_ending: str = '\n'):
        self.delimiter = delimiter
        self.line_ending = line_ending
        self.last_values: Dict[int, str] = {}
    
    def parse_line(self, line: str) -> Dict[int, str]:
        """Parse a line of CSV data into position->value mapping"""
        line = line.strip()
        if not line:
            return {}
        
        values = line.split(self.delimiter)
        parsed_data = {}
        
        for position, value in enumerate(values):
            parsed_data[position] = value.strip()
        
        # Update last known values
        self.last_values.update(parsed_data)
        
        return parsed_data
    
    def get_last_values(self) -> Dict[int, str]:
        """Get the last parsed values"""
        return self.last_values.copy()


class SerialReader:
    """Serial port reader with background thread"""
    
    def __init__(self, port: str, baudrate: int = 115200, **serial_kwargs):
        self.port = port
        self.baudrate = baudrate
        self.serial_kwargs = serial_kwargs
        self.serial_connection: Optional[serial.Serial] = None
        self.parser = SerialDataParser()
        
        # Threading
        self._running = False
        self._reader_thread: Optional[threading.Thread] = None
        
        # Data callbacks
        self._data_callbacks: List[Callable[[Dict[int, str]], None]] = []
        self._error_callbacks: List[Callable[[Exception], None]] = []
        
        # Statistics
        self.lines_received = 0
        self.lines_parsed = 0
        self.last_line_time = 0
    
    def add_data_callback(self, callback: Callable[[Dict[int, str]], None]):
        """Add callback for new data"""
        self._data_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[Exception], None]):
        """Add callback for errors"""
        self._error_callbacks.append(callback)
    
    def connect(self):
        """Connect to serial port"""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                **self.serial_kwargs
            )
            logging.info(pr_green(f"Connected to {self.port} at {self.baudrate} baud"))
        except serial.SerialException as e:
            logging.error(pr_red(f"Failed to connect to {self.port}: {e}"))
            self._notify_error(e)
            raise
    
    def disconnect(self):
        """Disconnect from serial port"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            logging.info(f"Disconnected from {self.port}")
    
    def start_reading(self):
        """Start background reading thread"""
        if self._running:
            logging.warning(pr_yellow("Reader already running"))
            return
        
        if not self.serial_connection or not self.serial_connection.is_open:
            self.connect()
        
        self._running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        logging.info("Started serial reading thread")
    
    def stop_reading(self):
        """Stop background reading thread"""
        if not self._running:
            return
        
        self._running = False
        if self._reader_thread:
            self._reader_thread.join(timeout=2)
        
        self.disconnect()
        logging.info("Stopped serial reading thread")
    
    def _read_loop(self):
        """Main reading loop (runs in background thread)"""
        buffer = ""
        
        while self._running:
            try:
                if not self.serial_connection or not self.serial_connection.is_open:
                    time.sleep(0.1)
                    continue
                
                # Read available data
                if self.serial_connection.in_waiting > 0:
                    data = self.serial_connection.read(self.serial_connection.in_waiting)
                    if data:
                        try:
                            decoded = data.decode('utf-8', errors='replace')
                            buffer += decoded
                        except UnicodeDecodeError:
                            logging.warning(pr_yellow("Failed to decode serial data"))
                            continue
                
                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self._process_line(line)
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
                
            except serial.SerialException as e:
                logging.error(pr_red(f"Serial error: {e}"))
                self._notify_error(e)
                break
            except Exception as e:
                logging.error(pr_red(f"Unexpected error in read loop: {e}"))
                self._notify_error(e)
                break
    
    def _process_line(self, line: str):
        """Process a single line of data"""
        self.lines_received += 1
        self.last_line_time = time.time()
        
        try:
            parsed_data = self.parser.parse_line(line)
            if parsed_data:
                self.lines_parsed += 1
                self._notify_data(parsed_data)
        except Exception as e:
            logging.warning(pr_yellow(f"Failed to parse line '{line}': {e}"))
    
    def _notify_data(self, data: Dict[int, str]):
        """Notify all data callbacks"""
        for callback in self._data_callbacks:
            try:
                callback(data)
            except Exception as e:
                logging.error(pr_red(f"Error in data callback: {e}"))
    
    def _notify_error(self, error: Exception):
        """Notify all error callbacks"""
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logging.error(pr_red(f"Error in error callback: {e}"))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reader statistics"""
        return {
            'port': self.port,
            'baudrate': self.baudrate,
            'connected': self.serial_connection.is_open if self.serial_connection else False,
            'running': self._running,
            'lines_received': self.lines_received,
            'lines_parsed': self.lines_parsed,
            'last_line_time': self.last_line_time,
            'time_since_last_line': time.time() - self.last_line_time if self.last_line_time > 0 else None
        }


def list_serial_ports() -> List[tuple]:
    """List available serial ports"""
    ports = []
    for port, desc, hwid in sorted(comports()):
        ports.append((port, desc, hwid))
    return ports


if __name__ == "__main__":
    # Test the serial reader
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    
    # List available ports
    ports = list_serial_ports()
    print("Available ports:")
    for i, (port, desc, hwid) in enumerate(ports):
        print(f"  {i+1}: {port} - {desc}")
    
    if ports:
        # Test with first available port
        test_port = ports[0][0]
        print(f"\nTesting with port: {test_port}")
        
        reader = SerialReader(test_port)
        
        def on_data(data):
            print(f"Received: {data}")
        
        def on_error(error):
            print(f"Error: {error}")
        
        reader.add_data_callback(on_data)
        reader.add_error_callback(on_error)
        
        try:
            reader.start_reading()
            time.sleep(10)  # Read for 10 seconds
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            reader.stop_reading()
    else:
        print("No serial ports found")