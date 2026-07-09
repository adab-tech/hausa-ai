# Unified launcher for Modal TTS training runs.
# Preflight -> launch -> persistent log -> auto-diagnosis on failure.
#
# Usage (from repo root):
#   .\utils\run_training.ps1                     # piper, 300 extra epochs
#   .\utils\run_training.ps1 -ExtraEpochs 600
#   .\utils\run_training.ps1 -ResumeCkpt "/checkpoints/piper_hausa_waxal/last.ckpt"

param(
    [int]$ExtraEpochs = 300,
    [int]$BatchSize = 16,
    [string]$ResumeCkpt = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Signature: windows-console-encoding
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$py = Join-Path $root ".venv\Scripts\python.exe"
$modal = Join-Path $root ".venv\Scripts\modal.exe"

Write-Host "=== Preflight ===" -ForegroundColor Cyan
& $py utils\preflight_train.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Preflight failed - not launching. Fix the problems above." -ForegroundColor Red
    exit 1
}

$logDir = Join-Path $root "logs\modal_runs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir ("piper_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))

Write-Host "=== Launching (log: $log) ===" -ForegroundColor Cyan
# --detach: the app survives client disconnects (laptop sleep) and finishes
# server-side — export + volume commit run in the function, no client needed
$trainArgs = @("run", "--detach", "finetune_piper_hausa_modal.py", "--extra-epochs", $ExtraEpochs, "--batch-size", $BatchSize)
if ($ResumeCkpt) { $trainArgs += @("--resume-ckpt", $ResumeCkpt) }

& $modal @trainArgs 2>&1 | Tee-Object -FilePath $log
$exit = $LASTEXITCODE

if ($exit -ne 0) {
    Write-Host "=== Run failed - diagnosing against known signatures ===" -ForegroundColor Yellow
    & $py utils\diagnose_run.py $log
} else {
    Write-Host "=== Run completed. Pull outputs with: ===" -ForegroundColor Green
    Write-Host "  modal volume get hausa-ai-checkpoints piper_hausa_waxal models/piper_hausa_waxal"
}
exit $exit
