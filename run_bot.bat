@echo off
echo ========================================
echo Starting dyarboot Discord Bot...
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Creating .env from env.example...
    copy env.example .env >nul 2>&1
    echo Please edit .env and add your DISCORD_TOKEN!
    pause
    exit /b 1
)

REM Install/update dependencies
echo Installing dependencies...
python -m pip install -r requirements.txt --quiet

echo.
echo Starting bot...
echo Press Ctrl+C to stop the bot
echo ========================================
echo.

python bot.py

pause

