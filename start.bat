@echo off
REM Startup script for Henrietta Dispatch Application (Windows)

echo =========================================
echo Henrietta Dispatch Application
echo =========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    echo Virtual environment created.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/update dependencies
echo Checking dependencies...
pip install -q -r requirements.txt

echo.
echo Starting application...
echo The app will open in your browser at http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo =========================================
echo.

REM Run the Streamlit app
streamlit run app/main.py

pause
