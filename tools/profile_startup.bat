@echo off
REM Profile Python import times for ChatGPT Sidebar
REM This script runs the app with import profiling enabled and generates a report

setlocal
set PYTHONWARNINGS=ignore

echo Profiling imports for ChatGPT Sidebar...
echo.

REM Run with import time profiling
python -X importtime -m chatgpt_sidebar 2> tools\import_profile.log

REM Parse and display results
echo.
echo Generating report...
python tools\report_imports.py tools\import_profile.log

echo.
echo Profile saved to: tools\import_profile.log
echo.
pause

