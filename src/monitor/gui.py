#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from monitor.config import MonitorConfig
from monitor.serial_reader import SerialReader, list_serial_ports


def time_ago(timestamp):
    """Convert timestamp to human-readable 'ago' format"""
    if timestamp == 0:
        return ""
    
    now = time.time()
    diff = now - timestamp
    
    if diff < 1:
        return "now"
    elif diff < 60:
        return f"{int(diff)}s ago"
    elif diff < 3600:
        minutes = int(diff / 60)
        return f"{minutes}m ago"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours}h ago"
    else:
        days = int(diff / 86400)
        return f"{days}d ago"


class StatusBar:
    """Status bar for connection and statistics info"""
    
    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        
        # Connection status
        self.connection_var = tk.StringVar()
        self.connection_var.set("Disconnected")
        self.connection_label = ttk.Label(
            self.frame,
            textvariable=self.connection_var,
            foreground='red'
        )
        self.connection_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Statistics
        self.stats_var = tk.StringVar()
        self.stats_var.set("Lines: 0 | Parsed: 0")
        self.stats_label = ttk.Label(self.frame, textvariable=self.stats_var)
        self.stats_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Last data time
        self.last_data_var = tk.StringVar()
        self.last_data_var.set("Last data: Never")
        self.last_data_label = ttk.Label(self.frame, textvariable=self.last_data_var)
        self.last_data_label.pack(side=tk.LEFT)
    
    def update_connection_status(self, connected: bool, port: str = ""):
        """Update connection status"""
        if connected:
            self.connection_var.set(f"Connected to {port}")
            self.connection_label.configure(foreground='green')
        else:
            self.connection_var.set("Disconnected")
            self.connection_label.configure(foreground='red')
    
    def update_stats(self, stats: Dict[str, Any]):
        """Update statistics display"""
        lines_received = stats.get('lines_received', 0)
        lines_parsed = stats.get('lines_parsed', 0)
        self.stats_var.set(f"Lines: {lines_received} | Parsed: {lines_parsed}")
        
        last_line_time = stats.get('last_line_time', 0)
        if last_line_time > 0:
            last_time_str = datetime.fromtimestamp(last_line_time).strftime('%H:%M:%S')
            self.last_data_var.set(f"Last data: {last_time_str}")


class SimpleMonitorGUI:
    """Simplified, robust GUI application for MCU data monitoring"""
    
    def __init__(self, config: MonitorConfig, port: str = None, baudrate: int = 115200):
        self.config = config
        self.port = port
        self.baudrate = baudrate
        self.serial_reader: Optional[SerialReader] = None
        self.tree_items: Dict[int, str] = {}  # position -> tree item id
        self.field_data: Dict[int, Dict] = {}  # position -> field metadata
        
        # Simple flags
        self.running = True
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(config.title)
        self.root.geometry(f"{config.window_size[0]}x{config.window_size[1]}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Setup UI first
        self.setup_ui()
        
        # Setup serial after UI is ready
        if self.port:
            self.setup_serial()
        
        # Simple timer for updates (no complex threading)
        self.schedule_updates()
        
        print("GUI initialized successfully")
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text=self.config.title,
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.connect_button = ttk.Button(
            control_frame,
            text="Connect" if not self.port else "Disconnect",
            command=self.toggle_connection
        )
        self.connect_button.pack(side=tk.LEFT, padx=(0, 10))
        
        clear_button = ttk.Button(
            control_frame,
            text="Clear Values",
            command=self.clear_values
        )
        clear_button.pack(side=tk.LEFT, padx=(0, 10))
        
        port_button = ttk.Button(
            control_frame,
            text="Select Port",
            command=self.select_port
        )
        port_button.pack(side=tk.LEFT)
        
        # Data table
        self.create_data_table(main_frame)
        
        # Status bar
        self.status_bar = StatusBar(main_frame)
        self.status_bar.frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        print("UI setup completed")
    
    def create_data_table(self, parent):
        """Create data table"""
        table_frame = ttk.Frame(parent)
        table_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        table_frame.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)
        
        # Simple columns
        columns = ['field', 'raw_value', 'formatted_value', 'status']
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        self.tree.heading('field', text='Field')
        self.tree.column('field', width=150, anchor='w')
        
        self.tree.heading('raw_value', text='Raw Value')
        self.tree.column('raw_value', width=150, anchor='e')
        
        self.tree.heading('formatted_value', text='Formatted Value')
        self.tree.column('formatted_value', width=150, anchor='e')
        
        self.tree.heading('status', text='Status')
        self.tree.column('status', width=200, anchor='w')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        
        # Initialize rows for each configured field
        self.initialize_table_rows()
        
        print(f"Table created with {len(self.tree_items)} rows")
    
    def initialize_table_rows(self):
        """Initialize table rows for configured fields"""
        positions = self.config.get_all_positions()
        
        for position in positions:
            field_config = self.config.get_field_config(position)
            field_name = field_config.get('label', f'Field {position}') if field_config else f'Field {position}'
            
            # Insert row
            item_id = self.tree.insert('', 'end', values=[field_name, '---', '---', 'No data'])
            
            # Store mapping
            self.tree_items[position] = item_id
            self.field_data[position] = {
                'last_received_time': 0,
                'last_changed_time': 0,
                'last_value': None
            }
    
    def setup_serial(self):
        """Setup serial connection"""
        try:
            self.serial_reader = SerialReader(self.port, self.baudrate)
            self.serial_reader.add_data_callback(self.on_serial_data)
            self.serial_reader.add_error_callback(self.on_serial_error)
            print(f"Serial reader setup for {self.port}")
        except Exception as e:
            print(f"Failed to setup serial: {e}")
            messagebox.showerror("Serial Error", f"Failed to setup serial connection: {e}")
    
    def toggle_connection(self):
        """Toggle serial connection"""
        try:
            if not self.serial_reader:
                if not self.port:
                    messagebox.showwarning("No Port", "Please select a port first using 'Select Port' button")
                    return
                self.setup_serial()
            
            if self.serial_reader and hasattr(self.serial_reader, '_running') and self.serial_reader._running:
                print("Disconnecting...")
                self.disconnect()
            else:
                print("Connecting...")
                self.connect()
        except Exception as e:
            print(f"Error in toggle_connection: {e}")
            messagebox.showerror("Connection Error", f"Error toggling connection: {e}")
    
    def connect(self):
        """Connect to serial port"""
        try:
            if not self.serial_reader:
                return
            
            self.serial_reader.start_reading()
            self.connect_button.configure(text="Disconnect")
            self.status_bar.update_connection_status(True, self.port)
            print(f"Connected to {self.port}")
        except Exception as e:
            print(f"Connection failed: {e}")
            messagebox.showerror("Connection Error", f"Failed to connect to {self.port}:\\n{e}")
    
    def disconnect(self):
        """Disconnect from serial port"""
        try:
            if self.serial_reader:
                self.serial_reader.stop_reading()
                self.connect_button.configure(text="Connect")
                self.status_bar.update_connection_status(False)
                print("Disconnected")
        except Exception as e:
            print(f"Disconnect error: {e}")
    
    def on_serial_data(self, data: Dict[int, str]):
        """Handle new serial data - SIMPLIFIED"""
        try:
            # print(f"Received data: {data}")  # Debug print
            
            # Schedule update on main thread - SIMPLE approach
            self.root.after_idle(lambda: self.update_table_simple(data))
            
        except Exception as e:
            print(f"Error in on_serial_data: {e}")
    
    def update_table_simple(self, data: Dict[int, str]):
        """Update table with new data - SIMPLIFIED"""
        try:
            current_time = time.time()
            
            for position, raw_value in data.items():
                if position in self.tree_items:
                    item_id = self.tree_items[position]
                    field_info = self.field_data[position]
                    
                    # Format value
                    try:
                        formatted_value = self.config.format_value(position, raw_value)
                    except Exception as e:
                        formatted_value = raw_value  # Fallback
                        print(f"Format error for position {position}: {e}")
                    
                    # Update timing
                    field_info['last_received_time'] = current_time
                    if field_info['last_value'] != formatted_value:
                        field_info['last_changed_time'] = current_time
                        field_info['last_value'] = formatted_value
                    
                    # Create status
                    status = f"rx: {time_ago(field_info['last_received_time'])}"
                    if field_info['last_changed_time'] > 0:
                        status += f" | ch: {time_ago(field_info['last_changed_time'])}"
                    
                    # Get current values and update
                    current_values = list(self.tree.item(item_id, 'values'))
                    field_name = current_values[0]  # Keep field name
                    
                    # Update row
                    self.tree.item(item_id, values=[field_name, raw_value, formatted_value, status])
                    
            # print(f"Updated table with {len(data)} values")
                    
        except Exception as e:
            print(f"Error updating table: {e}")
    
    def on_serial_error(self, error: Exception):
        """Handle serial errors"""
        print(f"Serial error: {error}")
        self.root.after_idle(lambda: messagebox.showerror("Serial Error", f"Serial error: {error}"))
    
    def select_port(self):
        """Simple port selection"""
        try:
            ports = list_serial_ports()
            if not ports:
                messagebox.showwarning("No Ports", "No serial ports found")
                return
            
            # Simple dialog
            port_window = tk.Toplevel(self.root)
            port_window.title("Select Port")
            port_window.geometry("400x300")
            port_window.transient(self.root)
            port_window.grab_set()
            
            ttk.Label(port_window, text="Select a port:", font=('Arial', 12)).pack(pady=10)
            
            listbox = tk.Listbox(port_window)
            listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            for port, desc, _ in ports:
                listbox.insert(tk.END, f"{port} - {desc}")
            
            def select():
                selection = listbox.curselection()
                if selection:
                    self.port = ports[selection[0]][0]
                    if self.serial_reader:
                        self.disconnect()
                    self.setup_serial()
                    port_window.destroy()
            
            ttk.Button(port_window, text="Select", command=select).pack(pady=10)
            
        except Exception as e:
            print(f"Error in port selection: {e}")
            messagebox.showerror("Error", f"Port selection error: {e}")
    
    def clear_values(self):
        """Clear all values"""
        try:
            for position, item_id in self.tree_items.items():
                current_values = list(self.tree.item(item_id, 'values'))
                field_name = current_values[0]
                self.tree.item(item_id, values=[field_name, '---', '---', 'Cleared'])
                self.field_data[position] = {
                    'last_received_time': 0,
                    'last_changed_time': 0,
                    'last_value': None
                }
            print("Values cleared")
        except Exception as e:
            print(f"Error clearing values: {e}")
    
    def schedule_updates(self):
        """Simple periodic updates"""
        if not self.running:
            return
        
        try:
            # Update stats
            if self.serial_reader:
                stats = self.serial_reader.get_stats()
                self.status_bar.update_stats(stats)
            
            # Update relative times
            current_time = time.time()
            for position, field_info in self.field_data.items():
                if position in self.tree_items and field_info['last_received_time'] > 0:
                    item_id = self.tree_items[position]
                    current_values = list(self.tree.item(item_id, 'values'))
                    
                    status = f"rx: {time_ago(field_info['last_received_time'])}"
                    if field_info['last_changed_time'] > 0:
                        status += f" | ch: {time_ago(field_info['last_changed_time'])}"
                    
                    # Only update status column
                    current_values[3] = status
                    self.tree.item(item_id, values=current_values)
            
        except Exception as e:
            print(f"Error in scheduled update: {e}")
        
        # Schedule next update
        if self.running:
            self.root.after(2000, self.schedule_updates)
    
    def on_closing(self):
        """Handle window closing"""
        print("Closing application...")
        self.running = False
        
        try:
            if self.serial_reader:
                self.disconnect()
        except:
            pass
        
        self.root.destroy()
    
    def run(self):
        """Start the application"""
        try:
            print("Starting GUI main loop...")
            self.root.mainloop()
        except Exception as e:
            print(f"GUI error: {e}")
            import traceback
            traceback.print_exc()


def create_demo_gui():
    """Create a demo GUI with sample configuration"""
    config = MonitorConfig()
    demo_config = config.create_example_config()
    config.load_from_dict(demo_config)
    
    gui = SimpleMonitorGUI(config)
    return gui


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    # Create and run demo GUI
    gui = create_demo_gui()
    gui.run()