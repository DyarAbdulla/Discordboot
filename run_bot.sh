#!/bin/bash

echo "========================================"
echo "Starting dyarboot Discord Bot..."
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "WARNING: .env file not found!"
    echo "Creating .env from env.example..."
    cp env.example .env
    echo "Please edit .env and add your DISCORD_TOKEN!"
    exit 1
fi

# Install/update dependencies
echo "Installing dependencies..."
python3 -m pip install -r requirements.txt --quiet

echo ""
echo "Starting bot..."
echo "Press Ctrl+C to stop the bot"
echo "========================================"
echo ""

python3 bot.py

