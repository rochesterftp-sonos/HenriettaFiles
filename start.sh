#!/bin/bash
# Startup script for Henrietta Dispatch Application

echo "========================================="
echo "Henrietta Dispatch Application"
echo "========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "Virtual environment created."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Checking dependencies..."
pip install -q -r requirements.txt

echo ""
echo "Starting application..."
echo "The app will open in your browser at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================="
echo ""

# Run the Streamlit app
streamlit run app/main.py
