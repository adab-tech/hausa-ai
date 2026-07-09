@echo off
echo ============================================================
echo             HAUSA AI — MODAL SETUP HELPER                  
echo ============================================================
echo.
echo Attempting to launch Modal setup...
echo (This should open a browser window to log in via GitHub)
echo.
set PYTHONIOENCODING=utf-8
".venv\Scripts\modal.exe" setup
if %errorlevel% neq 0 (
    echo.
    echo [INFO] Automatic setup browser launch was bypassed or failed.
    echo Attempting manual token generation...
    echo.
    ".venv\Scripts\modal.exe" token new
)
echo.
echo ============================================================
pause
