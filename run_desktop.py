import sys
import os
import subprocess
import time
import webbrowser
from pathlib import Path

def get_app_path() -> str:
    """Find the correct path to the Streamlit app.py script."""
    if getattr(sys, "frozen", False):
        # We are running in a PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # We are running in a normal Python environment
        base_path = Path(__file__).parent.resolve()
        
    app_path = base_path / "lecat" / "dashboard" / "app.py"
    if not app_path.exists():
        print(f"ERROR: Could not find app.py at {app_path}")
        sys.exit(1)
        
    return str(app_path)

def main():
    print("Starting LECAT Dashboard...")
    
    # Define port
    port = "8501"
    url = f"http://localhost:{port}"
    
    # Path to app.py
    app_path = get_app_path()
    
    # Command to run Streamlit
    # In a frozen environment, streamlit might be sys.executable -m streamlit
    # However, PyInstaller hooks for streamlit often require special handling.
    # The safest way in a bundled app is to use sys.executable and the streamlit module.
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_path,
        "--server.port",
        port,
        "--server.headless",
        "true"
    ]
    
    # Start the Streamlit server
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except Exception as e:
        print(f"Failed to start Streamlit server: {e}")
        sys.exit(1)
        
    print(f"Dashboard server started. Opening {url}...")
    
    # Wait a moment for server to initialize
    time.sleep(3)
    
    # Open browser
    webbrowser.open(url)
    
    print("\n" + "="*50)
    print("LECAT is running!")
    print(f"You can access the dashboard at: {url}")
    print("To stop the application, close this terminal window.")
    print("="*50 + "\n")
    
    # Keep the script running to hold the process open
    try:
        process.wait()
    except KeyboardInterrupt:
        print("\nShutting down LECAT...")
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
        print("Goodbye!")

if __name__ == "__main__":
    main()
