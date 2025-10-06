@echo off
REM ChatGPT Sidebar Launcher
REM This batch file provides easy access to run the ChatGPT Sidebar executable

echo Starting ChatGPT Sidebar...

REM Run the executable with default settings (embedded webview)
start "" "dist\ChatGPT_Sidebar.exe"

REM Alternative commands for different modes:
REM For native app mode (docks installed ChatGPT app):
REM start "" "dist\ChatGPT_Sidebar.exe" --native-app

REM For custom width:
REM start "" "dist\ChatGPT_Sidebar.exe" --width 500

REM For custom URL:
REM start "" "dist\ChatGPT_Sidebar.exe" --url https://chat.openai.com/

echo ChatGPT Sidebar launched successfully!
pause
