"""
Earnings Event Alpha Tool - Main Entry Point

Run this file to start the Streamlit dashboard:
    streamlit run main.py

Or run directly:
    python main.py
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Launch Streamlit app."""
    app_path = Path(__file__).parent / "src" / "ui" / "app.py"
    
    if not app_path.exists():
        print(f"Error: App file not found at {app_path}")
        sys.exit(1)
    
    print("Starting Earnings Event Alpha Tool...")
    print(f"Dashboard: http://localhost:8501")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        subprocess.run([
            "streamlit", "run", str(app_path),
            "--server.headless", "true",
            "--server.runOnSave", "true",
            "--server.fileWatcherType", "auto"
        ])
    except KeyboardInterrupt:
        print("\nShutting down...")
    except FileNotFoundError:
        print("\nError: Streamlit not found. Please install dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
