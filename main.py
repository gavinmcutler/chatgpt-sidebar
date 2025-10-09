"""Entry point for PyInstaller build."""

import sys
import os

# Get the directory where the executable is located
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    application_path = os.path.dirname(sys.executable)
else:
    # Running as script
    application_path = os.path.dirname(os.path.abspath(__file__))

# Change to the executable's directory to ensure proper working directory
os.chdir(application_path)

# Add src directory to path
sys.path.insert(0, os.path.join(application_path, 'src'))

from chatgpt_sidebar.app import main

if __name__ == "__main__":
    main()
