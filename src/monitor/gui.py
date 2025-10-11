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
    
    def __init__(self, parent, font_style='Status.TLabel'):
        self.frame = ttk.Frame(parent)
        
        # Connection status
        self.connection_var = tk.StringVar()
        self.connection_var.set("Disconnected")
        self.connection_label = ttk.Label(
            self.frame,
            textvariable=self.connection_var,
            foreground='red',
            style=font_style
        )
        self.connection_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Statistics
        self.stats_var = tk.StringVar()
        self.stats_var.set("Lines: 0 | Parsed: 0")
        self.stats_label = ttk.Label(self.frame, textvariable=self.stats_var, style=font_style)
        self.stats_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Last data time
        self.last_data_var = tk.StringVar()
        self.last_data_var.set("Last data: Never")
        self.last_data_label = ttk.Label(self.frame, textvariable=self.last_data_var, style=font_style)
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
        
        # Transformation controls
        self.transform_vars: Dict[int, tk.StringVar] = {}  # position -> selected transform
        self.transform_combos: Dict[int, ttk.Combobox] = {}  # position -> combobox widget
        self.combobox_positioned: bool = False  # Track if comboboxes have been positioned
        self.pending_reposition: Optional[str] = None  # Track pending repositioning
        
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
        """Setup the user interface with larger fonts for bench viewing"""
        # Configure larger fonts for better visibility from distance
        self.large_font = ('Arial', 14, 'normal')
        self.button_font = ('Arial', 12, 'normal')
        self.table_font = ('Arial', 12, 'normal')
        self.status_font = ('Arial', 11, 'normal')
        
        # Configure ttk styles for larger fonts
        style = ttk.Style()
        style.configure('Large.TButton', font=self.button_font)
        style.configure('Large.TLabel', font=self.large_font)
        style.configure('Status.TLabel', font=self.status_font)
        
        # Configure Treeview fonts
        style.configure('Treeview', font=self.table_font, rowheight=25)
        style.configure('Treeview.Heading', font=('Arial', 13, 'bold'))
        
        # Configure Combobox fonts
        style.configure('Large.TCombobox', font=self.table_font)
        
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
            font=('Arial', 24, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.connect_button = ttk.Button(
            control_frame,
            text="Connect" if not self.port else "Disconnect",
            command=self.toggle_connection,
            style='Large.TButton'
        )
        self.connect_button.pack(side=tk.LEFT, padx=(0, 10))
        
        clear_button = ttk.Button(
            control_frame,
            text="Clear Values",
            command=self.clear_values,
            style='Large.TButton'
        )
        clear_button.pack(side=tk.LEFT, padx=(0, 10))
        
        port_button = ttk.Button(
            control_frame,
            text="Select Port",
            command=self.select_port,
            style='Large.TButton'
        )
        port_button.pack(side=tk.LEFT)
        
        # Data table
        self.create_data_table(main_frame)
        
        # Status bar with larger fonts
        self.status_bar = StatusBar(main_frame, 'Status.TLabel')
        self.status_bar.frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        print("UI setup completed")
    
    def create_data_table(self, parent):
        """Create data table with transformation dropdowns"""
        table_frame = ttk.Frame(parent)
        table_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        table_frame.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)
        
        # Enhanced columns with transformation selector
        columns = ['field', 'raw_value', 'transformed_value', 'transform_select', 'status']
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Configure columns with larger widths for bigger fonts
        self.tree.heading('field', text='Field')
        self.tree.column('field', width=150, anchor='w')
        
        self.tree.heading('raw_value', text='Raw Value')
        self.tree.column('raw_value', width=150, anchor='e')
        
        self.tree.heading('transformed_value', text='Transformed Value')
        self.tree.column('transformed_value', width=220, anchor='e')
        
        self.tree.heading('transform_select', text='Transform')
        self.tree.column('transform_select', width=180, anchor='w')
        
        self.tree.heading('status', text='Status')
        self.tree.column('status', width=220, anchor='w')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        
        # Bind only essential events for combobox repositioning
        self.tree.bind('<Configure>', self.on_tree_configure)
        self.tree.bind('<MouseWheel>', self.on_scroll)
        self.tree.bind('<Button-4>', self.on_scroll)  # Linux scroll up
        self.tree.bind('<Button-5>', self.on_scroll)  # Linux scroll down
        
        # Initialize rows for each configured field
        self.initialize_table_rows()
        
        print(f"Table created with {len(self.tree_items)} rows")
    
    def initialize_table_rows(self):
        """Initialize table rows for configured fields with transformation dropdowns"""
        positions = self.config.get_all_positions()
        
        for position in positions:
            field_config = self.config.get_field_config(position)
            field_name = field_config.get('label', f'Field {position}') if field_config else f'Field {position}'
            
            # Create transformation options
            transform_options = ["Raw Value"]  # Default option
            transformations = field_config.get('transformations', []) if field_config else []
            
            for transform in transformations:
                label = transform.get('label', f'Transform {len(transform_options)}')
                transform_options.append(label)
            
            # Add "All Transforms" option if there are transformations
            if transformations:
                transform_options.append("All Transforms (Final)")
            
            # Create StringVar for this field's transformation selection
            self.transform_vars[position] = tk.StringVar()
            
            # Set default to "All Transforms" if available, otherwise "Raw Value"
            default_selection = "All Transforms (Final)" if transformations else "Raw Value"
            self.transform_vars[position].set(default_selection)
            
            # Insert row with placeholder for transform dropdown
            item_id = self.tree.insert('', 'end', values=[
                field_name, 
                '---', 
                '---', 
                '', # Placeholder for dropdown
                'No data'
            ])
            
            # Store mapping
            self.tree_items[position] = item_id
            self.field_data[position] = {
                'last_received_time': 0,
                'last_changed_time': 0,
                'last_value': None,
                'transform_options': transform_options,
                'transformations': transformations
            }
            
            # Create combobox for transformation selection (we'll position it later)
            combo = ttk.Combobox(
                self.tree, 
                textvariable=self.transform_vars[position],
                values=transform_options,
                state='readonly',
                width=18,
                style='Large.TCombobox'
            )
            combo.bind('<<ComboboxSelected>>', lambda e, pos=position: self.on_transform_changed(pos))
            self.transform_combos[position] = combo
    
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
    
    def on_scroll(self, event):
        """Handle scroll events - reposition comboboxes after scroll"""
        # Cancel any pending repositioning
        if self.pending_reposition:
            self.root.after_cancel(self.pending_reposition)
        
        # Schedule repositioning with a small delay
        self.pending_reposition = self.root.after(50, self.position_comboboxes_stable)

    def on_tree_configure(self, event):
        """Handle tree configure events with debouncing"""
        # Only reposition if the size actually changed or it's the first time
        if not self.combobox_positioned or (hasattr(event, 'width') and hasattr(event, 'height')):
            # Cancel any pending repositioning
            if self.pending_reposition:
                self.root.after_cancel(self.pending_reposition)
            
            # Schedule repositioning with a small delay to debounce
            self.pending_reposition = self.root.after(100, self.position_comboboxes_stable)

    def on_transform_changed(self, position: int):
        """Handle transformation selection change"""
        try:
            # Force a redraw with current data
            if position in self.field_data and self.field_data[position]['last_value'] is not None:
                # Get the last raw value if we have it
                item_id = self.tree_items[position]
                current_values = list(self.tree.item(item_id, 'values'))
                if len(current_values) >= 2 and current_values[1] != '---':
                    raw_value = current_values[1]
                    self.update_single_field(position, raw_value)
        except Exception as e:
            print(f"Error handling transform change for position {position}: {e}")

    def get_transformed_value(self, position: int, raw_value: str) -> str:
        """Get the transformed value based on current selection"""
        try:
            selected_transform = self.transform_vars[position].get()
            field_info = self.field_data[position]
            transformations = field_info.get('transformations', [])
            
            if selected_transform == "Raw Value":
                return self.config.format_value(position, raw_value)
            elif selected_transform == "All Transforms (Final)":
                return self.config.apply_all_transformations(position, raw_value)
            else:
                # Find the specific transformation
                transformation_steps = self.config.get_transformation_steps(position, raw_value)
                for step in transformation_steps:
                    if step['label'] == selected_transform:
                        return step['formatted']
                
                # Fallback to raw value
                return self.config.format_value(position, raw_value)
                
        except Exception as e:
            print(f"Error getting transformed value for position {position}: {e}")
            return self.config.format_value(position, raw_value)

    def update_single_field(self, position: int, raw_value: str):
        """Update a single field with new data"""
        try:
            current_time = time.time()
            item_id = self.tree_items[position]
            field_info = self.field_data[position]
            
            # Get transformed value based on current selection
            transformed_value = self.get_transformed_value(position, raw_value)
            
            # Update timing
            field_info['last_received_time'] = current_time
            if field_info['last_value'] != transformed_value:
                field_info['last_changed_time'] = current_time
                field_info['last_value'] = transformed_value
            
            # Create status
            status = f"rx: {time_ago(field_info['last_received_time'])}"
            if field_info['last_changed_time'] > 0:
                status += f" | ch: {time_ago(field_info['last_changed_time'])}"
            
            # Get current field name and update row
            current_values = list(self.tree.item(item_id, 'values'))
            field_name = current_values[0]  # Keep field name
            
            # Update row (leave transform column empty since we have the combobox)
            self.tree.item(item_id, values=[field_name, raw_value, transformed_value, '', status])
            
        except Exception as e:
            print(f"Error updating single field {position}: {e}")

    def update_table_simple(self, data: Dict[int, str]):
        """Update table with new data using transformations"""
        try:
            for position, raw_value in data.items():
                if position in self.tree_items:
                    self.update_single_field(position, raw_value)
                    
            # Only position comboboxes if they haven't been positioned yet
            if not self.combobox_positioned:
                self.root.after_idle(self.position_comboboxes_stable)
                    
        except Exception as e:
            print(f"Error updating table: {e}")

    def position_comboboxes_stable(self):
        """Position all comboboxes with stability tracking"""
        try:
            # Clear pending reposition
            self.pending_reposition = None
            
            for position, combo in self.transform_combos.items():
                if position in self.tree_items:
                    item_id = self.tree_items[position]
                    bbox = self.tree.bbox(item_id, 'transform_select')
                    if bbox:
                        # Adjust position relative to the tree widget
                        tree_x = self.tree.winfo_x()
                        tree_y = self.tree.winfo_y()
                        combo.place(x=tree_x + bbox[0] + 2, 
                                   y=tree_y + bbox[1] + 2, 
                                   width=bbox[2] - 4, 
                                   height=bbox[3] - 4)
                        combo.lift()  # Bring to front
            
            # Mark as positioned
            self.combobox_positioned = True
            
        except Exception as e:
            print(f"Error positioning comboboxes: {e}")

    def position_comboboxes(self):
        """Legacy method - kept for compatibility"""
        self.position_comboboxes_stable()
    
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
            
            ttk.Button(port_window, text="Select", command=select, style='Large.TButton').pack(pady=10)
            
        except Exception as e:
            print(f"Error in port selection: {e}")
            messagebox.showerror("Error", f"Port selection error: {e}")
    
    def clear_values(self):
        """Clear all values"""
        try:
            for position, item_id in self.tree_items.items():
                current_values = list(self.tree.item(item_id, 'values'))
                field_name = current_values[0]
                self.tree.item(item_id, values=[field_name, '---', '---', '', 'Cleared'])
                self.field_data[position] = {
                    'last_received_time': 0,
                    'last_changed_time': 0,
                    'last_value': None,
                    'transform_options': self.field_data[position].get('transform_options', []),
                    'transformations': self.field_data[position].get('transformations', [])
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
        print("Shutting down...")
        self.running = False
        
        try:
            # Clean up comboboxes
            for combo in self.transform_combos.values():
                combo.destroy()
            
            # Disconnect serial
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