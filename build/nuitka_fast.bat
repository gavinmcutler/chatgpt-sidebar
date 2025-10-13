@echo off
REM Nuitka Build - Maximum Performance
REM Compiles Python to native code with aggressive optimizations
REM Startup is 5-10x faster than PyInstaller onefile

echo ================================================================
echo  ChatGPT Sidebar - Nuitka Fast Build
echo ================================================================
echo.
echo NOTE: This build requires Nuitka and a C++ compiler (MSVC or Clang)
echo       Install: pip install nuitka
echo.

REM Check if Nuitka is installed
python -c "import nuitka" 2>nul
if errorlevel 1 (
    echo [ERROR] Nuitka is not installed!
    echo        Install with: pip install nuitka
    echo.
    pause
    exit /b 1
)

REM Clean previous builds
echo [1/3] Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist main.build rmdir /s /q main.build
if exist main.dist rmdir /s /q main.dist
if exist main.onefile-build rmdir /s /q main.onefile-build
if exist __pycache__ rmdir /s /q __pycache__

echo [2/3] Building with Nuitka (this may take 5-10 minutes)...
echo.

REM Build with Nuitka
python -m nuitka ^
  --standalone ^
  --onefile ^
  --enable-plugin=pyside6 ^
  --lto=yes ^
  --windows-disable-console ^
  --output-dir=dist ^
  --output-filename=ChatGPT_Sidebar.exe ^
  --nofollow-import-to=test ^
  --nofollow-import-to=unittest ^
  --nofollow-import-to=distutils ^
  --nofollow-import-to=setuptools ^
  --nofollow-import-to=pip ^
  --nofollow-import-to=tkinter ^
  --nofollow-import-to=numpy ^
  --nofollow-import-to=matplotlib ^
  --nofollow-import-to=pandas ^
  --windows-icon-from-ico=icon.ico ^
  main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Nuitka build failed!
    echo.
    echo Common issues:
    echo - Missing C++ compiler (install Visual Studio Build Tools)
    echo - Insufficient disk space (Nuitka needs ~2GB temp space)
    echo - Missing dependencies (pip install nuitka ordered-set)
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] Build complete!
echo.
echo ================================================================
echo  Output: dist\ChatGPT_Sidebar.exe
echo  Size: ~50-80MB (optimized native code)
echo  Startup: ~0.5-1s (10x faster than PyInstaller onefile)
echo ================================================================
echo.
pause

