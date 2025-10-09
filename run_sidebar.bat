@echo off
REM ChatGPT Sidebar Launcher

echo Starting ChatGPT Sidebar...

REM Set PYTHONPATH to include src directory
set PYTHONPATH=%~dp0src;%PYTHONPATH%

REM Run as Python module (for development)
python -m chatgpt_sidebar

REM Alternative: Run the executable (if built)
REM start "" "dist\ChatGPT_Sidebar\ChatGPT_Sidebar.exe"

REM Alternative commands for custom settings:
REM python -m chatgpt_sidebar --width 480
REM python -m chatgpt_sidebar --url https://chat.openai.com/
REM python -m chatgpt_sidebar --enable-logging
