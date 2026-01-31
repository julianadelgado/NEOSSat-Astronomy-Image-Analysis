# Simple FITS Tool

A cross-platform (Windows & macOS) desktop application inspired by space data finders. This tool allows you to download FITS files from a URL and visualize them using a simple GUI.

## Features

- **Download Tab**: Download FITS files directly from a URL. Includes progress bar tracking.
- **Visualize Tab**: Browse downloaded files and view them with automatic contrast scaling.
- **Cross-Platform**: Built with Python and PyQt6 to work seamlessly on Windows and macOS.

## Prerequisites

- Python 3.9 or higher
- [uv](https://github.com/astral-sh/uv) (Recommended for dependency management)

## Setup and Installation

1.  Navigate to the project directory:
    ```bash
    cd simple_fits_tool
    ```

2.  Run the application using `uv`:
    ```bash
    uv run main.py
    ```
    *This will automatically resolve and install the required dependencies (PyQt6, astropy, matplotlib, requests, numpy) in an isolated environment.*

    **Alternatively**, if you want to create a manual virtual environment:
    ```bash
    uv venv
    
    # Activate:
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate
    
    uv pip install -r pyproject.toml
    python main.py
    ```

## Usage

1.  **Download**:
    - Go to the "Download" tab.
    - Paste a link to a FITS file (e.g., from an archive).
    - Enter a desired filename (e.g., `sun.fits`).
    - Click **Download**.

2.  **Visualize**:
    - Switch to the "Visualize" tab.
    - Click file names in the list on the left.
    - The image will appear in the main view.

## Project Structure

- `main.py`: The entry point and main application code.
- `pyproject.toml`: Project configuration and dependencies.
- `data/`: The default folder where images are saved.
