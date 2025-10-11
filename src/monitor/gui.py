#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from .config import MonitorConfig
from .serial_reader import SerialReader, list_serial_ports



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


class FieldWidget:
    """Widget for displaying a single field value with transformations in a grid layout"""
    
    def __init__(self, parent, position: int, config: Dict[str, Any]):
        self.position = position
        self.config = config
        self.last_received_time = 0   # When any data was last received
        self.last_changed_time = 0    # When value actually changed
        self.last_value = None        # Track last value for change detection
        self.transformation_widgets = []  # Store transformation display widgets
        
        # Create main frame for this field row
        self.frame = ttk.Frame(parent, relief='solid', borderwidth=1)
        
        # Configure grid columns with fixed widths
        self.frame.grid_columnconfigure(0, minsize=120, weight=0)  # Label column
        self.frame.grid_columnconfigure(1, minsize=150, weight=0)  # Value column
        
        # Calculate transformation columns
        transformations = config.get('transformations', [])
        for i in range(len(transformations)):
            self.frame.grid_columnconfigure(2 + i*2, minsize=100, weight=0)     # Transform label
            self.frame.grid_columnconfigure(2 + i*2 + 1, minsize=120, weight=0) # Transform value
        
        # Time column (last)
        time_col = 2 + len(transformations) * 2
        self.frame.grid_columnconfigure(time_col, minsize=80, weight=1)  # Time indicators
        
        # Row label (field name)
        label_text = config.get('label', f'Field {position}')
        self.label = ttk.Label(
            self.frame, 
            text=label_text, 
            font=('Arial', 11, 'bold'),
            anchor='w',
            width=15
        )
        self.label.grid(row=0, column=0, padx=(8, 4), pady=8, sticky='w')
        
        # Original value display
        self.value_var = tk.StringVar()
        self.value_var.set('---')
        
        value_color = config.get('color', 'black')
        self.value_label = ttk.Label(
            self.frame, 
            textvariable=self.value_var,
            font=('Arial', 12, 'bold'),
            foreground=value_color,
            anchor='e',
            width=18
        )
        self.value_label.grid(row=0, column=1, padx=4, pady=8, sticky='e')
        
        # Create transformation columns
        self.setup_transformation_widgets()
        
        # Time indicators in the last column
        time_frame = ttk.Frame(self.frame)
        time_frame.grid(row=0, column=time_col, padx=(4, 8), pady=8, sticky='e')
        
        # Last received indicator
        self.received_var = tk.StringVar()
        self.received_label = ttk.Label(
            time_frame,
            textvariable=self.received_var,
            font=('Arial', 7),
            foreground='blue'
        )
        self.received_label.pack(anchor=tk.E)
        
        # Last changed indicator  
        self.changed_var = tk.StringVar()
        self.changed_label = ttk.Label(
            time_frame,
            textvariable=self.changed_var,
            font=('Arial', 7),
            foreground='green'
        )
        self.changed_label.pack(anchor=tk.E)
    
    def setup_transformation_widgets(self):
        """Create widgets for displaying transformation results"""
        transformations = self.config.get('transformations', [])
        
        for i, transformation in enumerate(transformations):
            label_col = 2 + i * 2      # Label column
            value_col = 2 + i * 2 + 1  # Value column
            
            # Transformation label
            trans_label = ttk.Label(
                self.frame,
                text=transformation.get('label', f'Transform {i+1}'),
                font=('Arial', 9, 'bold'),
                anchor='w',
                foreground='darkblue',
                width=12
            )
            trans_label.grid(row=0, column=label_col, padx=4, pady=8, sticky='w')
            
            # Transformation value
            trans_var = tk.StringVar()
            trans_var.set('---')
            trans_value_label = ttk.Label(
                self.frame,
                textvariable=trans_var,
                font=('Arial', 10),
                anchor='e',
                foreground='darkgreen',
                width=15
            )
            trans_value_label.grid(row=0, column=value_col, padx=4, pady=8, sticky='e')
            
            self.transformation_widgets.append({
                'label': trans_label,
                'value_var': trans_var,
                'value_label': trans_value_label,
                'config': transformation
            })
    
    def update_value(self, raw_value: str, formatted_value: str, transformed_values: List[Dict[str, str]]):
        """Update the displayed value and transformations, track both received and changed times"""
        current_time = time.time()
        value_changed = self.last_value != formatted_value
        
        # Always update received time
        self.last_received_time = current_time
        
        # Update changed time only if value actually changed
        if value_changed:
            self.last_changed_time = current_time
            # Flash effect only for actual changes
            if self.last_value != '---':  # Don't flash on initial value
                self.value_label.configure(background='lightblue')
                self.frame.after(200, lambda: self.value_label.configure(background=''))
        
        # Update main value
        self.value_var.set(formatted_value)
        self.last_value = formatted_value
        
        # Update transformation values
        for i, widget_info in enumerate(self.transformation_widgets):
            if i < len(transformed_values):
                trans_data = transformed_values[i]
                widget_info['value_var'].set(trans_data['value'])
                
                # Flash transformation if main value changed
                if value_changed and self.last_value != '---':
                    widget_info['value_label'].configure(background='lightgreen')
                    self.frame.after(300, lambda w=widget_info['value_label']: w.configure(background=''))
            else:
                widget_info['value_var'].set('---')
        
        # Update both time displays
        self.update_relative_times()
    
    def update_relative_times(self):
        """Update both relative time displays"""
        # Received time (blue)
        if self.last_received_time > 0:
            received_ago = time_ago(self.last_received_time)
            self.received_var.set(f"rx: {received_ago}" if received_ago else "rx: now")
        else:
            self.received_var.set("")
        
        # Changed time (green)
        if self.last_changed_time > 0:
            changed_ago = time_ago(self.last_changed_time)
            self.changed_var.set(f"ch: {changed_ago}" if changed_ago else "ch: now")
        else:
            self.changed_var.set("")


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
        self.field_widgets: Dict[int, FieldWidget] = {}
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(config.title)
        self.root.geometry(f"{config.window_size[0]}x{config.window_size[1]}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.setup_ui()
        self.setup_serial()
        
        # Auto-update timers
        self.update_stats_timer()
        self.update_relative_times_timer()
    
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
        ).pack(side=tk.LEFT)
        
        # Fields container with scrollbar
        fields_container = ttk.Frame(main_frame)
        fields_container.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        fields_container.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Canvas and scrollbar for scrolling
        canvas = tk.Canvas(fields_container)
        scrollbar = ttk.Scrollbar(fields_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        fields_container.rowconfigure(0, weight=1)
        fields_container.columnconfigure(0, weight=1)
        
        # Create field widgets
        self.create_field_widgets()
        
        # Status bar
        self.status_bar = StatusBar(main_frame)
        self.status_bar.frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def create_field_widgets(self):
        """Create widgets for all configured fields"""
        positions = self.config.get_all_positions()
        
        # Create header row
        self.create_header_row()
        
        for i, position in enumerate(positions):
            field_config = self.config.get_field_config(position)
            widget = FieldWidget(self.scrollable_frame, position, field_config)
            widget.frame.grid(row=i+1, column=0, sticky=(tk.W, tk.E), pady=1, padx=2)
            self.scrollable_frame.columnconfigure(0, weight=1)
            
            self.field_widgets[position] = widget
    
    def create_header_row(self):
        """Create a header row showing column titles"""
        header_frame = ttk.Frame(self.scrollable_frame, relief='solid', borderwidth=2)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 2), padx=2)
        
        # Configure columns same as field widgets
        header_frame.grid_columnconfigure(0, minsize=120, weight=0)  # Field name
        header_frame.grid_columnconfigure(1, minsize=150, weight=0)  # Raw value
        
        # Find maximum transformations to set up columns
        max_transforms = 0
        for pos in self.config.get_all_positions():
            field_config = self.config.get_field_config(pos)
            transforms = field_config.get('transformations', []) if field_config else []
            max_transforms = max(max_transforms, len(transforms))
        
        # Set up transformation columns
        for i in range(max_transforms):
            header_frame.grid_columnconfigure(2 + i*2, minsize=100, weight=0)
            header_frame.grid_columnconfigure(2 + i*2 + 1, minsize=120, weight=0)
        
        # Time column
        time_col = 2 + max_transforms * 2
        header_frame.grid_columnconfigure(time_col, minsize=80, weight=1)
        
        # Header labels
        ttk.Label(header_frame, text="Field", font=('Arial', 10, 'bold'), foreground='navy').grid(
            row=0, column=0, padx=(8, 4), pady=4, sticky='w')
        ttk.Label(header_frame, text="Raw Value", font=('Arial', 10, 'bold'), foreground='navy').grid(
            row=0, column=1, padx=4, pady=4, sticky='e')
        
        # Generic transformation headers
        for i in range(max_transforms):
            ttk.Label(header_frame, text=f"Transform {i+1}", font=('Arial', 9, 'bold'), foreground='darkblue').grid(
                row=0, column=2 + i*2, padx=4, pady=4, sticky='w')
            ttk.Label(header_frame, text="Value", font=('Arial', 9, 'bold'), foreground='darkblue').grid(
                row=0, column=2 + i*2 + 1, padx=4, pady=4, sticky='e')
        
        ttk.Label(header_frame, text="Status", font=('Arial', 9, 'bold'), foreground='purple').grid(
            row=0, column=time_col, padx=(4, 8), pady=4, sticky='e')
    
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
                
                # Recreate field widgets
                for widget in self.field_widgets.values():
                    widget.frame.destroy()
                self.field_widgets.clear()
                
                self.create_field_widgets()
                self.root.title(self.config.title)
                
                messagebox.showinfo("Success", f"Configuration loaded from {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load configuration:\n{e}")
    
    def clear_values(self):
        """Clear all displayed values"""
        for widget in self.field_widgets.values():
            widget.value_var.set('---')
            widget.received_var.set('')
            widget.changed_var.set('')
            widget.last_value = None
            widget.last_received_time = 0
            widget.last_changed_time = 0
            
            # Clear transformation values
            for trans_widget in widget.transformation_widgets:
                trans_widget['value_var'].set('---')
    
    def on_serial_data(self, data: Dict[int, str]):
        """Handle new serial data"""
        # Update widgets on main thread
        self.root.after(0, self._update_widgets, data)
    
    def _update_widgets(self, data: Dict[int, str]):
        """Update field widgets with new data (runs on main thread)"""
        for position, raw_value in data.items():
            if position in self.field_widgets:
                formatted_value = self.config.format_value(position, raw_value)
                transformed_values = self.config.get_transformed_values(position, raw_value)
                self.field_widgets[position].update_value(raw_value, formatted_value, transformed_values)
    
    def on_serial_error(self, error: Exception):
        """Handle serial errors"""
        self.root.after(0, self._show_error, error)
    
    def _show_error(self, error: Exception):
        """Show error message (runs on main thread)"""
        messagebox.showerror("Serial Error", f"Serial communication error:\n{error}")
        self.disconnect()
    
    def update_stats_timer(self):
        """Update statistics display periodically"""
        if self.serial_reader:
            stats = self.serial_reader.get_stats()
            self.status_bar.update_stats(stats)
        
        # Schedule next update
        self.root.after(1000, self.update_stats_timer)
    
    def update_relative_times_timer(self):
        """Update relative time displays every second"""
        for widget in self.field_widgets.values():
            widget.update_relative_times()
        
        # Schedule next update
        self.root.after(1000, self.update_relative_times_timer)
    
    def on_closing(self):
        """Handle window closing"""
        if self.serial_reader:
            self.disconnect()
        self.root.destroy()
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()


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
