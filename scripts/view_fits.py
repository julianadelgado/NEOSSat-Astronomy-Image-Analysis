
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
        
        # Listbox with Scrollbar
        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.file_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        
        ttk.Button(left_panel, text="Rescan Directory", command=self.scan_files).pack(fill=tk.X, pady=5)

        # Right Panel: Image Display
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.fig, self.ax = plt.subplots(figsize=(5, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.all_files = []
        self.scan_files()

    def scan_files(self):
        self.all_files = []
        self.file_listbox.delete(0, tk.END)
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
            
            # Populate listbox (initially with all files)
            for file_path in self.all_files:
                try:
                    relative_path = file_path.relative_to(PROJECT_ROOT)
                    self.file_listbox.insert(tk.END, str(relative_path))
                except ValueError:
                    # Should not happen if searching from PROJECT_ROOT
                    self.file_listbox.insert(tk.END, str(file_path))
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to scan directory: {e}")

    def filter_files(self, *args):
        search_term = self.search_var.get().lower()
        self.file_listbox.delete(0, tk.END)
        
        for file_path in self.all_files:
            try:
                relative_path = str(file_path.relative_to(PROJECT_ROOT))
            except ValueError:
                relative_path = str(file_path)
                
            if search_term in relative_path.lower():
                self.file_listbox.insert(tk.END, relative_path)

    def on_file_select(self, event):
        selection = self.file_listbox.curselection()
        if not selection:
            return
        
        file_rel_path = self.file_listbox.get(selection[0])
        file_path = PROJECT_ROOT / file_rel_path
        
        self.display_fits(file_path)

    def display_fits(self, file_path):
        try:
            with fits.open(file_path) as hdul:
                # Find image data (usually in primary or first extension)
                data = None
                
                # Check HDUs
                for i, hdu in enumerate(hdul):
                    if hdu.data is not None:
                        # Ensure it's image data (2D or more)
                        if getattr(hdu, 'is_image', False) or (isinstance(hdu.data, np.ndarray) and hdu.data.ndim >= 2):
                            data = hdu.data
                            break
                
                if data is None:
                    self.ax.clear()
                    self.ax.text(0.5, 0.5, "No image data found in FITS", ha='center')
                    self.ax.axis('off')
                    self.canvas.draw()
                    return

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
            print(f"Error loading {file_path}: {e}")

if __name__ == "__main__":
    if not (PROJECT_ROOT / ".venv").exists():
        print(f"Warning: .venv not found at {PROJECT_ROOT / '.venv'}. Ensure dependencies are installed.")
    
    root = tk.Tk()
    app = FitsViewerApp(root)
    root.mainloop()
