@echo off
REM Benchmark startup time of the built executable
REM Measures cold start latency

echo ================================================================
echo  ChatGPT Sidebar - Startup Benchmark
echo ================================================================
echo.

if not exist dist\ChatGPT_Sidebar.exe (
    if not exist dist\ChatGPT_Sidebar\ChatGPT_Sidebar.exe (
        echo [ERROR] No executable found!
        echo        Build first with: build\pyinstaller_onedir.bat
        echo                      or: build\nuitka_fast.bat
        pause
        exit /b 1
    )
    set "EXE_PATH=dist\ChatGPT_Sidebar\ChatGPT_Sidebar.exe"
) else (
    set "EXE_PATH=dist\ChatGPT_Sidebar.exe"
)

echo Testing: %EXE_PATH%
echo.
echo Running 5 cold-start measurements...
echo (Executable will open and close automatically)
echo.

for /L %%i in (1,1,5) do (
    echo Run %%i/5...
    powershell -Command "$start = Get-Date; Start-Process '%EXE_PATH%' -PassThru | ForEach-Object { Start-Sleep -Milliseconds 2000; Stop-Process -Id $_.Id -Force }; $elapsed = ((Get-Date) - $start).TotalMilliseconds; Write-Host \"  Startup time: $([math]::Round($elapsed, 0)) ms\""
    timeout /t 2 /nobreak >nul
)

echo.
echo ================================================================
echo Benchmark complete!
echo.
echo Expected results:
echo - PyInstaller onefile:  3000-5000 ms
echo - PyInstaller onedir:    800-1500 ms  
echo - Nuitka onefile:        500-1000 ms
echo ================================================================
echo.
pause

