# Launch post-training validation after Modal VITS training completes.
# Prerequisites: models/vits/best_model.onnx + config.json (from Modal volume export)
$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
Set-Location $RepoRoot
$env:PYTHONIOENCODING = "utf-8"

$PythonCandidates = @(
    (Join-Path $RepoRoot ".venv\Scripts\python.exe"),
    "C:\Users\Adamu\Desktop\HAUSA AI\.venv\Scripts\python.exe",
    "python"
)
$Python = $PythonCandidates | Where-Object { $_ -eq "python" -or (Test-Path $_) } | Select-Object -First 1
if (-not $Python) { throw "Python not found. Create .venv and pip install -r backend/requirements-inference.txt" }

function Run-Step($Label, $Script) {
    Write-Host ""
    Write-Host ("=" * 60)
    Write-Host " $Label"
    Write-Host ("=" * 60)
    & $Python $Script
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Label" }
}

Write-Host "Hausa AI post-training pipeline"
Write-Host "Repo: $RepoRoot"
Write-Host "Python: $Python"

if (-not (Test-Path "models\vits\best_model.onnx")) {
    Write-Host ""
    Write-Host "Missing models/vits/best_model.onnx"
    Write-Host "Download from Modal volume:"
    Write-Host '  modal volume get hausa-ai-checkpoints waxal_hausa_vits_v1-June-05-2026_06+35AM-0000000/best_model.onnx models/vits/best_model.onnx'
    Write-Host '  modal volume get hausa-ai-checkpoints waxal_hausa_vits_v1-June-05-2026_06+35AM-0000000/config.json models/vits/config.json'
    exit 1
}

Run-Step "Phase 1 — Linguistic audit" "sovereign_auditor.py"
Run-Step "Phase 1 — VITS synthesis eval" "test_custom_vits.py"
Run-Step "Phase 2 — Latency / RTF benchmark" "flywheel_optimizer.py"
if (Test-Path "test_plurals_tone.py") {
    Run-Step "Phase 1 — Plural/tone eval" "test_plurals_tone.py"
}

Write-Host ""
Write-Host "Post-training checks complete."
Write-Host "Outputs: output_tests/*.wav"
Write-Host "Next: start backend + frontend and test live voice with speaker dial (Murya)."
