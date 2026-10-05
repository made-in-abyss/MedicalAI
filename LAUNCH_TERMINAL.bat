@echo off
title PHARMA-TERMINAL // Autonomous Reformulation Engine
color 0b
cls

echo ==============================================================================
echo    [PHARMA-TERMINAL] Autonomous Drug Reformulation & AI Debate Suite
echo ==============================================================================
echo.
echo [*] Checking local Ollama engine status...

:: Check if Ollama is running, start if not
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] Ollama service is already online.
) else (
    echo [*] Starting background Ollama GPU service...
    start "" /B "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
    timeout /t 3 /nobreak >nul
)

echo [*] Launching Pharma-CLI interactive interface...
echo.

:: Launch the CLI script in the same terminal
python "%~dp0pharma_cli.py"

echo.
echo [!] Session closed.
pause
