@echo off
cd /d "%~dp0review_app"

:: Create isolated virtual environment if needed
if not exist .venv\Scripts\python.exe (
  echo.
  echo  Creating virtual environment...
  python -m venv .venv
)

set "PYTHON=.venv\Scripts\python.exe"

:: Install dependencies into the app venv if needed
"%PYTHON%" -c "import fastapi, uvicorn, dotenv, google.genai" >nul 2>&1 || "%PYTHON%" -m pip install -r requirements.txt

:: Check .env exists
if not exist .env (
  echo.
  echo  ERROR: review_app\.env not found.
  echo  Copy review_app\.env.example to review_app\.env and fill in:
  echo    GEMINI_API_KEY
  echo    SMTP_PASS  (Google Workspace App Password)
  echo.
  pause
  exit /b 1
)

echo.
echo  Starting Buteforce Outreach Review...
echo  Open your browser at: http://localhost:8765
echo  Press Ctrl+C to stop.
echo.

start "" http://localhost:8765
"%PYTHON%" app.py
