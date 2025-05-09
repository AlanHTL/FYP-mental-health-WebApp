@echo off
echo Starting Mental Health Diagnosis System Backend...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv

    echo Virtual environment created successfully!
    REM Activate virtual environment and upgrade pip
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    echo Upgrading pip...
    python -m pip install --upgrade pip
    echo Installing requirements...
    python -m pip install -r requirements.txt
    
    echo requirements installed successfully!
) else (
    echo Virtual environment found.
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    
)

echo.
echo Starting the server...
echo The API will be available at: http://localhost:8000
echo API documentation will be available at: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server
python run.py

pause 