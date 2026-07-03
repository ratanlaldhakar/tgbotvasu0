@echo off
echo ============================================
echo   AI Productivity Telegram Bot
echo ============================================
echo.

set PYTHON=C:\Users\pc\AppData\Local\Programs\Python\Python313\python.exe

:: Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and fill in your credentials.
    pause
    exit /b 1
)

:: Check if python exists
if not exist "%PYTHON%" (
    echo ERROR: Python not found at %PYTHON%
    echo Please install Python 3.13 from https://python.org
    pause
    exit /b 1
)

echo Starting bot...
echo Press Ctrl+C to stop.
echo.

"%PYTHON%" app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bot stopped with an error. Check the output above.
    pause
)
