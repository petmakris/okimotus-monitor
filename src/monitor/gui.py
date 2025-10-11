#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import time
import threading
import queue
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


class MonitorGUI:
    """Main GUI application for MCU data monitoring"""
    
    def __init__(self, config: MonitorConfig, port: str = None, baudrate: int = 115200):
        self.config = config
        self.port = port
        self.baudrate = baudrate
        self.serial_reader: Optional[SerialReader] = None
        self.tree_items: Dict[int, Dict] = {}
        self.running = True
        
        # Use a queue for thread-safe communication
        self.data_queue = queue.Queue()
        self.update_lock = threading.Lock()
        
        # Timers
        self.stats_timer_id = None
        self.time_timer_id = None
        self.queue_timer_id = None
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(config.title)
        self.root.geometry(f"{config.window_size[0]}x{config.window_size[1]}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Make window responsive
        self.root.resizable(True, True)
        
        self.setup_ui()
        self.setup_serial()
        
        # Ensure GUI is ready before starting timers
        self.root.update_idletasks()
        
        # Start timers with better intervals
        self.start_timers()
    
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
            text="Connect",
            command=self.toggle_connection
        )
        self.connect_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            control_frame,
            text="Clear Values",
            command=self.clear_values
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            control_frame,
            text="Select Port",
            command=self.select_port
        ).pack(side=tk.LEFT)
        
        # Data table using Treeview for better alignment
        table_frame = ttk.Frame(main_frame)
        table_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        table_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Create treeview with columns
        self.create_data_table(table_frame)
        
        # Status bar
        self.status_bar = StatusBar(main_frame)
        self.status_bar.frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def create_data_table(self, parent):
        """Create a properly aligned data table using Treeview"""
        # Calculate columns based on configured transformations
        positions = self.config.get_all_positions()
        max_transforms = 0
        for pos in positions:
            field_config = self.config.get_field_config(pos)
            transforms = field_config.get('transformations', []) if field_config else []
            max_transforms = max(max_transforms, len(transforms))
        
        # Define columns
        columns = ['field', 'raw_value']
        column_headings = ['Field', 'Raw Value']
        
        # Add transformation columns
        for i in range(max_transforms):
            columns.extend([f'transform_{i+1}', f'value_{i+1}'])
            column_headings.extend([f'Transform {i+1}', 'Value'])
        
        columns.append('status')
        column_headings.append('Status')
        
        # Create treeview
        self.tree = ttk.Treeview(parent, columns=columns, show='headings', height=15)
        
        # Configure column headings and widths
        self.tree.heading('field', text='Field')
        self.tree.column('field', width=120, anchor='w')
        
        self.tree.heading('raw_value', text='Raw Value')
        self.tree.column('raw_value', width=150, anchor='e')
        
        # Configure transformation columns
        for i in range(max_transforms):
            transform_col = f'transform_{i+1}'
            value_col = f'value_{i+1}'
            
            self.tree.heading(transform_col, text=f'Transform {i+1}')
            self.tree.column(transform_col, width=100, anchor='w')
            
            self.tree.heading(value_col, text='Value')
            self.tree.column(value_col, width=120, anchor='e')
        
        self.tree.heading('status', text='Status')
        self.tree.column('status', width=80, anchor='e')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid the widgets
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        
        # Initialize tree items for each field
        self.tree_items = {}
        for position in positions:
            field_config = self.config.get_field_config(position)
            field_name = field_config.get('label', f'Field {position}') if field_config else f'Field {position}'
            
            # Create initial row data
            row_data = [field_name, '---']
            
            # Add empty transformation columns
            for i in range(max_transforms):
                row_data.extend(['---', '---'])
            
            row_data.append('---')  # Status column
            
            # Insert item and store reference
            item_id = self.tree.insert('', 'end', values=row_data)
            self.tree_items[position] = {
                'item_id': item_id,
                'last_received_time': 0,
                'last_changed_time': 0,
                'last_value': None
            }
    
    def start_timers(self):
        """Start all periodic timers with better intervals"""
        try:
            logging.debug("Starting GUI timers...")
            
            # Process data queue frequently but with smaller batches
            self.process_data_queue()
            
            # Update stats less frequently  
            self.update_stats_timer()
            
            # Update times even less frequently
            self.update_relative_times_timer()
            
            logging.debug("GUI timers started successfully")
        except Exception as e:
            logging.error(f"Error starting timers: {e}")
    
    def process_data_queue(self):
        """Process incoming data from queue (runs frequently)"""
        if not self.running:
            return
        
        try:
            # Process up to 10 items per cycle to avoid blocking
            processed = 0
            for _ in range(10):
                try:
                    data = self.data_queue.get_nowait()
                    self._update_widgets_safe(data)
                    processed += 1
                except queue.Empty:
                    break
                    
            # Log if we processed data (for debugging)
            if processed > 0:
                logging.debug(f"Processed {processed} data items from queue")
                
        except Exception as e:
            logging.warning(f"Error processing data queue: {e}")
        
        # Schedule next queue processing (faster interval)
        if self.running:
            self.queue_timer_id = self.root.after(50, self.process_data_queue)
    
    def create_field_widgets(self):
        """Legacy method - now replaced by create_data_table"""
        pass  # This method is no longer needed but kept for compatibility
    
    def create_header_row(self):
        """Legacy method - now replaced by Treeview headers"""
        pass  # This method is no longer needed but kept for compatibility
    
    def setup_serial(self):
        """Setup serial connection"""
        if self.port:
            self.serial_reader = SerialReader(self.port, self.baudrate)
            self.serial_reader.add_data_callback(self.on_serial_data)
            self.serial_reader.add_error_callback(self.on_serial_error)
    
    def toggle_connection(self):
        """Toggle serial connection"""
        if not self.serial_reader:
            if not self.port:
                messagebox.showerror("No Port", "No serial port specified. Please restart with -p option.")
                return
            self.setup_serial()
        
        if self.serial_reader._running:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        """Connect to serial port"""
        if not self.serial_reader:
            return
        
        try:
            self.serial_reader.start_reading()
            self.connect_button.configure(text="Disconnect")
            self.status_bar.update_connection_status(True, self.port)
            logging.info(f"Connected to {self.port}")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to {self.port}:\n{e}")
            logging.error(f"Connection failed: {e}")
    
    def disconnect(self):
        """Disconnect from serial port"""
        if self.serial_reader:
            self.serial_reader.stop_reading()
            self.connect_button.configure(text="Connect")
            self.status_bar.update_connection_status(False)
            logging.info("Disconnected")
    
    def select_port(self):
        """Show port selection dialog"""
        ports = list_serial_ports()
        
        if not ports:
            messagebox.showwarning("No Ports", "No serial ports found")
            return
        
        # Simple port selection dialog
        port_window = tk.Toplevel(self.root)
        port_window.title("Select Serial Port")
        port_window.geometry("400x300")
        port_window.transient(self.root)
        port_window.grab_set()
        
        ttk.Label(port_window, text="Select a serial port:", font=('Arial', 12)).pack(pady=10)
        
        # Port listbox
        listbox_frame = ttk.Frame(port_window)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        listbox = tk.Listbox(listbox_frame)
        scrollbar_ports = ttk.Scrollbar(listbox_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar_ports.set)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_ports.pack(side=tk.RIGHT, fill=tk.Y)
        
        for port, desc, hwid in ports:
            listbox.insert(tk.END, f"{port} - {desc}")
        
        # Baudrate selection
        baudrate_frame = ttk.Frame(port_window)
        baudrate_frame.pack(pady=10)
        
        ttk.Label(baudrate_frame, text="Baudrate:").pack(side=tk.LEFT, padx=(0, 10))
        baudrate_var = tk.StringVar(value=str(self.baudrate))
        baudrate_combo = ttk.Combobox(
            baudrate_frame,
            textvariable=baudrate_var,
            values=['9600', '19200', '38400', '57600', '115200', '230400', '460800', '921600'],
            width=10
        )
        baudrate_combo.pack(side=tk.LEFT)
        
        # Buttons
        button_frame = ttk.Frame(port_window)
        button_frame.pack(pady=20)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                selected_port = ports[selection[0]][0]
                selected_baudrate = int(baudrate_var.get())
                
                # Disconnect current connection
                if self.serial_reader:
                    self.disconnect()
                
                # Update settings
                self.port = selected_port
                self.baudrate = selected_baudrate
                self.setup_serial()
                
                port_window.destroy()
        
        ttk.Button(button_frame, text="Select", command=on_select).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=port_window.destroy).pack(side=tk.LEFT)
    
    def select_port(self):
        """Show port selection dialog"""
        try:
            ports = list_serial_ports()
            
            if not ports:
                messagebox.showwarning("No Ports", "No serial ports found")
                return
            
            # Simple selection using a dialog
            port_names = [f"{port} - {desc}" for port, desc, hwid in ports]
            
            # Create a simple selection window
            selection_window = tk.Toplevel(self.root)
            selection_window.title("Select Serial Port")
            selection_window.geometry("500x400")
            selection_window.transient(self.root)
            selection_window.grab_set()
            
            # Port list
            ttk.Label(selection_window, text="Available Serial Ports:", font=('Arial', 12)).pack(pady=10)
            
            listbox = tk.Listbox(selection_window, height=10)
            listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            for port_name in port_names:
                listbox.insert(tk.END, port_name)
            
            # Baudrate
            baudrate_frame = ttk.Frame(selection_window)
            baudrate_frame.pack(pady=10)
            
            ttk.Label(baudrate_frame, text="Baudrate:").pack(side=tk.LEFT, padx=(0, 10))
            baudrate_var = tk.StringVar(value=str(self.baudrate))
            baudrate_combo = ttk.Combobox(
                baudrate_frame,
                textvariable=baudrate_var,
                values=['9600', '19200', '38400', '57600', '115200', '230400'],
                width=10,
                state='readonly'
            )
            baudrate_combo.pack(side=tk.LEFT)
            
            # Buttons
            button_frame = ttk.Frame(selection_window)
            button_frame.pack(pady=20)
            
            def on_select():
                selection = listbox.curselection()
                if selection:
                    selected_port = ports[selection[0]][0]
                    selected_baudrate = int(baudrate_var.get())
                    
                    # Disconnect current connection
                    if self.serial_reader:
                        self.disconnect()
                    
                    # Update settings
                    self.port = selected_port
                    self.baudrate = selected_baudrate
                    self.setup_serial()
                    
                    selection_window.destroy()
            
            ttk.Button(button_frame, text="Select", command=on_select).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="Cancel", command=selection_window.destroy).pack(side=tk.LEFT)
            
        except Exception as e:
            logging.error(f"Error in port selection: {e}")
            messagebox.showerror("Error", f"Failed to list serial ports: {e}")

    def load_config(self):
        """Load configuration from file"""
        filename = filedialog.askopenfilename(
            title="Select Configuration File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                new_config = MonitorConfig(config_file=filename)
                self.config = new_config
                
                # Recreate data table
                self.tree.destroy()
                self.create_data_table(self.tree.master)
                self.root.title(self.config.title)
                
                messagebox.showinfo("Success", f"Configuration loaded from {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load configuration:\n{e}")
    
    def clear_values(self):
        """Clear all displayed values"""
        try:
            with self.update_lock:
                for position, item_info in self.tree_items.items():
                    # Get current field name (first column)
                    current_values = list(self.tree.item(item_info['item_id'], 'values'))
                    field_name = current_values[0]
                    
                    # Reset all values except field name
                    new_values = [field_name] + ['---'] * (len(current_values) - 1)
                    self.tree.item(item_info['item_id'], values=new_values)
                    
                    # Reset time tracking
                    item_info['last_received_time'] = 0
                    item_info['last_changed_time'] = 0
                    item_info['last_value'] = None
        except Exception as e:
            logging.warning(f"Error clearing values: {e}")
    
    def on_serial_data(self, data: Dict[int, str]):
        """Handle new serial data - thread safe"""
        if self.running:
            try:
                # Just put data in queue, don't block
                self.data_queue.put(data)
            except Exception as e:
                logging.warning(f"Error queuing data: {e}")
    
    def _update_widgets_safe(self, data: Dict[int, str]):
        """Update table with new data safely"""
        if not self.running:
            return
        
        try:
            with self.update_lock:
                current_time = time.time()
                
                for position, raw_value in data.items():
                    if position in self.tree_items:
                        self._update_single_item(position, raw_value, current_time)
        except Exception as e:
            logging.warning(f"Error updating widgets: {e}")
    
    def _update_single_item(self, position: int, raw_value: str, current_time: float):
        """Update a single tree item"""
        try:
            item_info = self.tree_items[position]
            formatted_value = self.config.format_value(position, raw_value)
            transformed_values = self.config.get_transformed_values(position, raw_value)
            
            # Check if value changed
            value_changed = item_info['last_value'] != formatted_value
            
            # Update timing
            item_info['last_received_time'] = current_time
            if value_changed:
                item_info['last_changed_time'] = current_time
                item_info['last_value'] = formatted_value
            
            # Build new row data
            current_values = list(self.tree.item(item_info['item_id'], 'values'))
            field_name = current_values[0]  # Keep field name
            
            new_values = [field_name, formatted_value]
            
            # Add transformation values
            for trans_data in transformed_values:
                new_values.extend([trans_data.get('label', '---'), trans_data.get('value', '---')])
            
            # Pad with empty transformation columns if needed
            max_transforms = (len(current_values) - 3) // 2
            while len(transformed_values) < max_transforms:
                new_values.extend(['---', '---'])
            
            # Add status column
            status_text = self._format_status(item_info)
            new_values.append(status_text)
            
            # Update the tree item
            self.tree.item(item_info['item_id'], values=new_values)
            
        except Exception as e:
            logging.warning(f"Error updating item {position}: {e}")
    
    def _format_status(self, item_info):
        """Format status text showing last received/changed times"""
        status_parts = []
        
        if item_info['last_received_time'] > 0:
            rx_ago = time_ago(item_info['last_received_time'])
            status_parts.append(f"rx: {rx_ago}" if rx_ago else "rx: now")
        
        if item_info['last_changed_time'] > 0:
            ch_ago = time_ago(item_info['last_changed_time'])
            status_parts.append(f"ch: {ch_ago}" if ch_ago else "ch: now")
        
        return " | ".join(status_parts) if status_parts else "---"
    
    def on_serial_error(self, error: Exception):
        """Handle serial errors"""
        self.root.after(0, self._show_error, error)
    
    def _show_error(self, error: Exception):
        """Show error message (runs on main thread)"""
        messagebox.showerror("Serial Error", f"Serial communication error:\n{error}")
        self.disconnect()
    
    def update_stats_timer(self):
        """Update statistics display periodically"""
        if not self.running:
            return
        
        try:
            if self.serial_reader:
                stats = self.serial_reader.get_stats()
                self.status_bar.update_stats(stats)
        except Exception as e:
            logging.warning(f"Error updating stats: {e}")
        
        # Schedule next update (longer interval)
        if self.running:
            self.stats_timer_id = self.root.after(2000, self.update_stats_timer)

    def update_relative_times_timer(self):
        """Update relative time displays every few seconds"""
        if not self.running:
            return
        
        try:
            with self.update_lock:
                for position, item_info in self.tree_items.items():
                    # Update status column with current time info
                    current_values = list(self.tree.item(item_info['item_id'], 'values'))
                    if len(current_values) > 0:
                        # Update only the status column (last column)
                        status_text = self._format_status(item_info)
                        current_values[-1] = status_text
                        self.tree.item(item_info['item_id'], values=current_values)
        except Exception as e:
            logging.warning(f"Error updating relative times: {e}")
        
        # Schedule next update (even longer interval)
        if self.running:
            self.time_timer_id = self.root.after(5000, self.update_relative_times_timer)

    def on_closing(self):
        """Handle window closing"""
        self.running = False
        
        # Cancel all timers
        for timer_id in [self.stats_timer_id, self.time_timer_id, self.queue_timer_id]:
            if timer_id:
                try:
                    self.root.after_cancel(timer_id)
                except:
                    pass
        
        # Disconnect serial
        if self.serial_reader:
            self.disconnect()
        
        # Give time for cleanup
        self.root.after(100, self.root.destroy)
    
    def run(self):
        """Start the GUI application"""
        try:
            # Ensure the GUI is properly initialized
            self.root.update()
            
            # Add a simple test to ensure GUI is responsive
            logging.info("GUI initialized, starting main loop...")
            
            # Test that the GUI can process events
            def test_responsiveness():
                logging.debug("GUI responsiveness test - event loop is working")
                self.root.after(5000, test_responsiveness)  # Test every 5 seconds
            
            test_responsiveness()
            
            # Start the main event loop
            self.root.mainloop()
        except KeyboardInterrupt:
            logging.info("Application interrupted by user")
            self.on_closing()
        except Exception as e:
            logging.error(f"GUI error: {e}")
            import traceback
            traceback.print_exc()
            self.on_closing()


def create_demo_gui():
    """Create a demo GUI with sample configuration"""
    config = MonitorConfig()
    demo_config = config.create_example_config()
    config.load_from_dict(demo_config)
    
    gui = MonitorGUI(config)
    return gui


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    # Create and run demo GUI
    gui = create_demo_gui()
    gui.run()
