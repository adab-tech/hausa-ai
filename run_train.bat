@echo off
echo ============================================================
echo             HAUSA AI — MODAL TRAINING LAUNCHER             
echo ============================================================
echo.
echo Launching serverless Hausa VITS training on Modal...
echo.
set PYTHONIOENCODING=utf-8
".venv\Scripts\modal.exe" run train_modal.py
echo.
echo ============================================================
pause
