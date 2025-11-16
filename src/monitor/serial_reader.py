#!/usr/bin/env python3

import logging
import threading
import time
from queue import Empty, Full, Queue
from typing import List, Dict, Any, Optional, Callable, Iterator, Mapping

import serial
from serial.tools.list_ports import comports


class SerialLine(Mapping[int, str]):
    """Represents a parsed line along with raw text and metadata."""

    def __init__(self, values: Dict[int, str], raw: str, timestamp: float, line_number: int):
        self.values = values
        self.raw = raw
        self.timestamp = timestamp
        self.line_number = line_number

    def __getitem__(self, key: int) -> str:
        return self.values[key]

    def __iter__(self) -> Iterator[int]:
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)

    def get(self, key: int, default: Optional[str] = None) -> Optional[str]:
        return self.values.get(key, default)

    def to_dict(self) -> Dict[int, str]:
        """Return a copy of the parsed values as a regular dictionary."""
        return dict(self.values)

    def copy(self) -> "SerialLine":
        """Clone the line, ensuring downstream consumers can't mutate shared state."""
        return SerialLine(values=dict(self.values), raw=self.raw, timestamp=self.timestamp, line_number=self.line_number)


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
    
    def __init__(self, port: str, baudrate: int = 115200, *, queue_size: int = 1024, **serial_kwargs):
        self.port = port
        self.baudrate = baudrate
        self.serial_kwargs = serial_kwargs
        self.serial_connection: Optional[serial.Serial] = None
        self.parser = SerialDataParser()
        
        # Threading
        self._running = False
        self._reader_thread: Optional[threading.Thread] = None
        
        # Data callbacks
        self._data_callbacks: List[Callable[[SerialLine], None]] = []
        self._error_callbacks: List[Callable[[Exception], None]] = []

        # Queue for consumer-facing reads
        self._data_queue: "Queue[SerialLine]" = Queue(maxsize=max(1, queue_size))
        
        # Statistics
        self.lines_received = 0
        self.lines_parsed = 0
        self.last_line_time = 0
    
    def add_data_callback(self, callback: Callable[[SerialLine], None]):
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
            logging.info(f"Connected to {self.port} at {self.baudrate} baud")
        except serial.SerialException as e:
            logging.error(f"Failed to connect to {self.port}: {e}")
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
            logging.warning("Reader already running")
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

    def close(self):
        """Public alias for stop_reading to match file-like semantics."""
        self.stop_reading()

    @property
    def running(self) -> bool:
        return self._running

    def read_line(self, timeout: Optional[float] = None) -> Optional[SerialLine]:
        """Blocking read that returns the next parsed line or None on timeout."""
        if not self._running:
            self.start_reading()
        try:
            return self._data_queue.get(timeout=timeout)
        except Empty:
            return None
    
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
                            logging.warning("Failed to decode serial data")
                            continue
                
                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self._process_line(line)
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
                
            except serial.SerialException as e:
                logging.error(f"Serial error: {e}")
                self._notify_error(e)
                break
            except Exception as e:
                logging.error(f"Unexpected error in read loop: {e}")
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
                payload = SerialLine(
                    values=parsed_data,
                    raw=line,
                    timestamp=self.last_line_time,
                    line_number=self.lines_received
                )
                self._notify_data(payload)
        except Exception as e:
            logging.warning(f"Failed to parse line '{line}': {e}")
    
    def _notify_data(self, data: SerialLine):
        """Notify all data callbacks"""
        for callback in self._data_callbacks:
            try:
                callback(data)
            except Exception as e:
                logging.error(f"Error in data callback: {e}")
        try:
            self._data_queue.put_nowait(data.copy())
        except Full:
            try:
                _ = self._data_queue.get_nowait()
            except Empty:
                pass
            try:
                self._data_queue.put_nowait(data.copy())
            except Full:
                pass
    
    def _notify_error(self, error: Exception):
        """Notify all error callbacks"""
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logging.error(f"Error in error callback: {e}")
    
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
    """List available serial ports, filtering out generic/unknown ports"""
    ports = []
    for port, desc, hwid in sorted(comports()):
        # Filter out ports with meaningless descriptions
        if desc and desc.lower() not in ['n/a', 'unknown', '']:
            ports.append((port, desc, hwid))
        # Also include ports that might have useful hardware IDs even if desc is poor
        elif hwid and 'USB' in hwid.upper() and desc.lower() == 'n/a':
            # Keep USB devices even if description is n/a
            ports.append((port, f"USB Device ({port})", hwid))
    
    # If no meaningful ports found, fall back to showing all ports
    # (in case user has unusual setup)
    if not ports:
        for port, desc, hwid in sorted(comports()):
            ports.append((port, desc or 'Unknown', hwid))
    
    return ports


class MultiPortSerialReader:
    """Manages multiple serial port readers"""
    
    def __init__(self, port_configs: Dict[str, int], **serial_kwargs):
        """
        Initialize multi-port reader
        
        Args:
            port_configs: Dictionary mapping port names to baudrates {'/dev/ttyUSB0': 115200, ...}
            **serial_kwargs: Additional serial port arguments
        """
        self.port_configs = port_configs
        self.serial_kwargs = serial_kwargs
        
        # Create a SerialReader for each port with its specific baudrate
        self.readers: Dict[str, SerialReader] = {}
        for port, baudrate in port_configs.items():
            self.readers[port] = SerialReader(port, baudrate, **serial_kwargs)
        
        # Callbacks
        self._data_callbacks: List[Callable[[str, SerialLine], None]] = []  # (port, data)
        self._error_callbacks: List[Callable[[str, Exception], None]] = []  # (port, error)
        
        # Setup callbacks for each reader
        for port, reader in self.readers.items():
            reader.add_data_callback(lambda data, p=port: self._on_port_data(p, data))
            reader.add_error_callback(lambda error, p=port: self._on_port_error(p, error))
    
    def add_data_callback(self, callback: Callable[[str, Dict[int, str]], None]):
        """Add callback for new data. Signature: callback(port, data)"""
        self._data_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[str, Exception], None]):
        """Add callback for errors. Signature: callback(port, error)"""
        self._error_callbacks.append(callback)
    
    def _on_port_data(self, port: str, data: Dict[int, str]):
        """Handle data from a specific port"""
        for callback in self._data_callbacks:
            try:
                callback(port, data)
            except Exception as e:
                logging.error(f"Error in data callback for port {port}: {e}")
    
    def _on_port_error(self, port: str, error: Exception):
        """Handle error from a specific port"""
        for callback in self._error_callbacks:
            try:
                callback(port, error)
            except Exception as e:
                logging.error(f"Error in error callback for port {port}: {e}")
    
    def start_reading(self):
        """Start reading from all ports"""
        for port, reader in self.readers.items():
            try:
                reader.start_reading()
                logging.info(f"Started reading from {port}")
            except Exception as e:
                logging.error(f"Failed to start reading from {port}: {e}")
                self._on_port_error(port, e)
    
    def stop_reading(self):
        """Stop reading from all ports"""
        for port, reader in self.readers.items():
            try:
                reader.stop_reading()
                logging.info(f"Stopped reading from {port}")
            except Exception as e:
                logging.error(f"Error stopping {port}: {e}")
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all ports"""
        stats = {}
        for port, reader in self.readers.items():
            stats[port] = reader.get_stats()
        return stats
    
    def get_reader(self, port: str) -> Optional[SerialReader]:
        """Get the SerialReader for a specific port"""
        return self.readers.get(port)


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
