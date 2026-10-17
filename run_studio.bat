@echo off
REM ==============================================================================
REM shrtnotes - 1-Click Studio Launcher (Windows)
REM ==============================================================================

cd /d "%~dp0"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    venv\Scripts\pip install flask markdown pyyaml
)

echo Launching shrtnotes Studio...
venv\Scripts\python.exe app.py
pause
