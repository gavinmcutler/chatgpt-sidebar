# ChatGPT Sidebar - Executable Build

## Overview
This document provides information about the standalone executable version of ChatGPT Sidebar.

## Files Generated

### Main Executable
- **`dist/ChatGPT_Sidebar.exe`** - The main executable file (approximately 225 MB)
  - Contains all dependencies bundled into a single file
  - No Python installation required on target systems
  - Windows-only application

### Launch Scripts
- **`run_sidebar.bat`** - Convenient batch file to launch the application
- **`chatgpt_sidebar.spec`** - PyInstaller specification file used to build the executable

## Usage

### Basic Usage
Simply double-click `ChatGPT_Sidebar.exe` or run:
```cmd
dist\ChatGPT_Sidebar.exe
```

### Command Line Options
The executable supports the same command-line arguments as the Python script:

```cmd
# Default mode (embedded webview)
dist\ChatGPT_Sidebar.exe

# Custom width
dist\ChatGPT_Sidebar.exe --width 500

# Custom URL
dist\ChatGPT_Sidebar.exe --url https://chat.openai.com/

# Combined options
dist\ChatGPT_Sidebar.exe --width 480 --url https://chat.openai.com/
```

### Using the Batch File
For convenience, use the provided batch file:
```cmd
run_sidebar.bat
```

## System Requirements

- **Operating System**: Windows 10/11 (64-bit)
- **Memory**: At least 4GB RAM recommended
- **Disk Space**: 250MB free space for the executable
- **Internet**: Required for ChatGPT web access

## Features Included

 **Docked Sidebar** - Windows AppBar integration  
 **Embedded ChatGPT** - Built-in webview  
 **Screenshot-to-Chat** - Capture and insert screenshots  
 **Theme Integration** - Automatic light/dark mode detection  
 **Persistent Settings** - Remembers preferences  
 **Undock/Redock** - Toggle between docked and windowed modes  

## Troubleshooting

### Application Won't Start
1. Ensure you're running on Windows 10/11
2. Check that antivirus software isn't blocking the executable
3. Try running as administrator if needed

### WebView Issues
1. Ensure internet connection is available
2. Check firewall settings for web access
3. Check if you can access the ChatGPT website in your regular browser

### Performance Issues
1. Close other resource-intensive applications
2. Ensure sufficient RAM is available (4GB+ recommended)
3. Check disk space availability

## Distribution

### Sharing the Executable
To share the ChatGPT Sidebar with others:
1. Copy the entire `dist` folder
2. Include this README file
3. Ensure the target system meets requirements
4. No additional installation steps required

### File Size
The executable is approximately 225 MB due to:
- PySide6 Qt framework
- QtWebEngine components
- Python runtime
- All required dependencies

## Building from Source

If you need to rebuild the executable:

1. Install PyInstaller:
   ```cmd
   pip install pyinstaller
   ```

2. Run the build command:
   ```cmd
   python -m PyInstaller chatgpt_sidebar.spec
   ```

3. The executable will be created in the `dist` folder

## Support

For issues or questions:
1. Check the main project README.md
2. Review the troubleshooting section above
3. Ensure system requirements are met

## Version Information

- **Build Date**: January 2025
- **PyInstaller Version**: 6.15.0
- **Python Version**: 3.12.6
- **Target Platform**: Windows 64-bit
