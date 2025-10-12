#!/usr/bin/env python3
"""
Quick test to verify color support in the GUI
"""

import tkinter as tk
from tkinter import ttk

# Test if Treeview color tags work
root = tk.Tk()
root.title("Color Tag Test")
root.geometry("600x300")

tree = ttk.Treeview(root, columns=['field', 'value'], show='headings')
tree.heading('field', text='Field')
tree.heading('value', text='Value')

# Configure color tags
colors = ['red', 'green', 'blue', 'orange', 'purple', 'black']
for color in colors:
    tree.tag_configure(color, foreground=color)

# Insert test rows with different colors
tree.insert('', 'end', values=['Red Field', '123'], tags=('red',))
tree.insert('', 'end', values=['Green Field', '456'], tags=('green',))
tree.insert('', 'end', values=['Blue Field', '789'], tags=('blue',))
tree.insert('', 'end', values=['Orange Field', '101'], tags=('orange',))
tree.insert('', 'end', values=['Purple Field', '202'], tags=('purple',))
tree.insert('', 'end', values=['Black Field (default)', '303'], tags=('black',))

tree.pack(fill='both', expand=True, padx=10, pady=10)

label = ttk.Label(root, text="If you see different colored field names above, color tags work!")
label.pack(pady=10)

root.mainloop()
