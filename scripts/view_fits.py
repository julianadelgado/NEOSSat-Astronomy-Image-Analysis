
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from astropy.io import fits
from pathlib import Path
import numpy as np

# Ensure project root is in path or correctly referenced
PROJECT_ROOT = Path(__file__).resolve().parent.parent

class FitsViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FITS Image Viewer")
        self.root.geometry("1000x800")

        # Layout
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Panel: File List
        left_panel = ttk.Frame(main_frame, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        ttk.Label(left_panel, text="FITS Files found:").pack(anchor=tk.W, pady=(0, 5))
        
        # Search/Filter
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_files)
        ttk.Entry(left_panel, textvariable=self.search_var).pack(fill=tk.X, pady=5)
        
        # Treeview with Scrollbar
        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.file_tree = ttk.Treeview(list_frame, selectmode="browse", show="tree")
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_tree.bind('<<TreeviewSelect>>', self.on_file_select)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_tree.config(yscrollcommand=scrollbar.set)
        
        ttk.Button(left_panel, text="Rescan Directory", command=self.scan_files).pack(fill=tk.X, pady=5)

        # Right Panel: Image Display and Metadata
        right_panel = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        image_frame = ttk.Frame(right_panel)
        right_panel.add(image_frame, weight=3)
        
        self.fig, self.ax = plt.subplots(figsize=(5, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=image_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        metadata_frame = ttk.Frame(right_panel)
        right_panel.add(metadata_frame, weight=1)
        
        ttk.Label(metadata_frame, text="Image Info & Metadata:").pack(anchor=tk.W)
        self.metadata_text = tk.Text(metadata_frame, wrap=tk.NONE, height=10)
        
        metadata_scroll_y = ttk.Scrollbar(metadata_frame, orient=tk.VERTICAL, command=self.metadata_text.yview)
        metadata_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        metadata_scroll_x = ttk.Scrollbar(metadata_frame, orient=tk.HORIZONTAL, command=self.metadata_text.xview)
        metadata_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.metadata_text.config(yscrollcommand=metadata_scroll_y.set, xscrollcommand=metadata_scroll_x.set)
        self.metadata_text.pack(fill=tk.BOTH, expand=True)
        
        self.all_files = []
        self.scan_files()

    def scan_files(self):
        self.all_files = []
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        self.search_var.set("")
        
        # Walk through project root
        try:
            # Exclude directories
            exclude_dirs = {'.venv', '.git', '__pycache__', 'node_modules', '.idea', '.vscode'}
            
            for path in PROJECT_ROOT.rglob("*"):
                # Check if path is in excluded dir
                if any(part in exclude_dirs for part in path.parts):
                    continue
                    
                if path.is_file() and path.suffix.lower() in ['.fits', '.fit']:
                    self.all_files.append(path)
            
            # Sort files
            self.all_files.sort()
            
            self.populate_tree()
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to scan directory: {e}")

    def populate_tree(self, search_term=""):
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
            
        folders = {}
        for file_path in self.all_files:
            try:
                rel_path = file_path.relative_to(PROJECT_ROOT)
                parent_dir = str(rel_path.parent)
                if parent_dir == ".":
                    parent_dir = "Root"
            except ValueError:
                parent_dir = "Other"
                
            if search_term and search_term not in file_path.name.lower() and search_term not in parent_dir.lower():
                continue
                
            if parent_dir not in folders:
                folders[parent_dir] = self.file_tree.insert("", tk.END, text=parent_dir, open=True)
                
            self.file_tree.insert(folders[parent_dir], tk.END, text=file_path.name, values=(str(file_path),))

    def filter_files(self, *args):
        search_term = self.search_var.get().lower()
        self.populate_tree(search_term)

    def on_file_select(self, event):
        selection = self.file_tree.selection()
        if not selection:
            return
            
        item = selection[0]
        # Only process file items, not folder items
        values = self.file_tree.item(item, 'values')
        if not values:
            return
            
        file_path = Path(values[0])
        self.display_fits(file_path)

    def display_fits(self, file_path):
        try:
            with fits.open(file_path) as hdul:
                # Find image data (usually in primary or first extension)
                data = None
                header = None
                
                # Check HDUs
                for i, hdu in enumerate(hdul):
                    if hdu.data is not None:
                        # Ensure it's image data (2D or more)
                        if getattr(hdu, 'is_image', False) or (isinstance(hdu.data, np.ndarray) and hdu.data.ndim >= 2):
                            data = hdu.data
                            header = hdu.header
                            break
                            
                self.metadata_text.delete(1.0, tk.END)
                
                if data is None:
                    self.ax.clear()
                    self.ax.text(0.5, 0.5, "No image data found in FITS", ha='center')
                    self.ax.axis('off')
                    self.canvas.draw()
                    self.metadata_text.insert(tk.END, "No image data found.\n")
                    return

                # Display metadata and dimensions
                if header is not None:
                    metadata_str = f"Image dimensions: {data.shape}\n"
                    metadata_str += f"Data type: {data.dtype}\n"
                    metadata_str += "-" * 40 + "\n"
                    metadata_str += "FITS Header Metadata:\n"
                    for key, value in header.items():
                        metadata_str += f"{key:8s} = {value}\n"
                    self.metadata_text.insert(tk.END, metadata_str)

                # If 3D (e.g., data cube), take first slice
                while data.ndim > 2:
                    data = data[0]

                # Normalize for display
                # Use percentile invalid handling
                data = np.nan_to_num(data)
                vmin, vmax = np.percentile(data, [1, 99])
                
                self.ax.clear()
                self.ax.imshow(data, cmap='gray', vmin=vmin, vmax=vmax, origin='lower')
                self.ax.set_title(file_path.name)
                self.ax.axis('off')
                self.canvas.draw()
                
        except Exception as e:
            self.ax.clear()
            self.ax.text(0.5, 0.5, f"Error loading FITS:\n{str(e)}", ha='center', wrap=True)
            self.ax.axis('off')
            self.canvas.draw()
            self.metadata_text.delete(1.0, tk.END)
            self.metadata_text.insert(tk.END, f"Error loading FITS:\n{str(e)}\n")
            print(f"Error loading {file_path}: {e}")

if __name__ == "__main__":
    if not (PROJECT_ROOT / ".venv").exists():
        print(f"Warning: .venv not found at {PROJECT_ROOT / '.venv'}. Ensure dependencies are installed.")
    
    root = tk.Tk()
    app = FitsViewerApp(root)
    root.mainloop()
