@echo off
echo ============================================================
echo          HAUSA AI — POST-TRAINING VALIDATION
echo ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0post_train.ps1"
pause
