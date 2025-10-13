@echo off
REM PyInstaller OneDir Build - Fast Startup Version
REM This build extracts files once to a directory instead of on every launch
REM Startup is 3-5x faster than onefile builds

echo ================================================================
echo  ChatGPT Sidebar - PyInstaller OneDir Build
echo ================================================================
echo.

REM Clean previous builds
echo [1/3] Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

echo [2/3] Building with PyInstaller (onedir mode)...
echo.

REM Build with PyInstaller using onedir mode for faster startup
pyinstaller ^
  --name ChatGPT_Sidebar ^
  --onedir ^
  --noconsole ^
  --clean ^
  --strip ^
  --noconfirm ^
  --add-data "src;src" ^
  --hidden-import=PySide6.QtCore ^
  --hidden-import=PySide6.QtGui ^
  --hidden-import=PySide6.QtWidgets ^
  --hidden-import=PySide6.QtWebEngineCore ^
  --hidden-import=PySide6.QtWebEngineWidgets ^
  --exclude-module=tkinter ^
  --exclude-module=test ^
  --exclude-module=unittest ^
  --exclude-module=pdb ^
  --exclude-module=doctest ^
  --exclude-module=pydoc ^
  --exclude-module=xmlrpc ^
  --exclude-module=distutils ^
  --exclude-module=setuptools ^
  --exclude-module=pip ^
  --exclude-module=pkg_resources ^
  --exclude-module=importlib_metadata ^
  --exclude-module=numpy ^
  --exclude-module=matplotlib ^
  --exclude-module=pandas ^
  --exclude-module=scipy ^
  main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Build complete!
echo.
echo ================================================================
echo  Output: dist\ChatGPT_Sidebar\
echo  Executable: dist\ChatGPT_Sidebar\ChatGPT_Sidebar.exe
echo ================================================================
echo.
echo TIP: For distribution, zip the entire "ChatGPT_Sidebar" folder
echo      Users extract and run ChatGPT_Sidebar.exe
echo.
pause

