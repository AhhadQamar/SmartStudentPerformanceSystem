@echo off
REM Windows version of setup.sh: creates the venv, installs packages,
REM trains the model, seeds the database and starts the app.
REM WARNING: seeding wipes the database and recreates the demo data.

echo ==================================
echo  Smart Student Performance System
echo ==================================
echo.

echo Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo Could not create the virtual environment. Is Python installed and on PATH?
    pause
    exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo Installing packages...
pip install -r requirements.txt
if errorlevel 1 (
    echo Package installation failed.
    pause
    exit /b 1
)

echo.
echo Training the model...
python scripts\train_model.py
if errorlevel 1 (
    echo Model training failed.
    pause
    exit /b 1
)

echo.
echo Creating the database with demo data...
python scripts\seed.py
if errorlevel 1 (
    echo Seeding the database failed.
    pause
    exit /b 1
)

echo.
echo Starting the app at http://127.0.0.1:5000
echo Press Ctrl+C to stop.
echo.
set FLASK_APP=app
flask run
pause
