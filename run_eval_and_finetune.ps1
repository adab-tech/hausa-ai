# Eval + finetune orchestration for Hausa AI
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
$ModalCandidates = @(
    (Join-Path $RepoRoot ".venv\Scripts\modal.exe"),
    "C:\Users\Adamu\Desktop\HAUSA AI\.venv\Scripts\modal.exe"
)
$Modal = $ModalCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

Write-Host "Hausa AI — Eval + Finetune pipeline"
Write-Host "Python: $Python"

# ── Phase A: Post-training TTS eval ──────────────────────────────────────────
& "$RepoRoot\post_train.ps1"

# ── Phase B: Prepare Robinson LLM SFT dataset ───────────────────────────────
Write-Host ""
Write-Host "Building Robinson SFT dataset..."
& $Python (Join-Path $RepoRoot "utils\build_robinson_sft.py")

# ── Phase C: Backend unit tests ─────────────────────────────────────────────
Write-Host ""
Write-Host "Running backend pytest..."
Push-Location (Join-Path $RepoRoot "backend")
& $Python -m pytest -q --no-cov 2>&1 | Select-Object -Last 5
Pop-Location

# ── Phase D: Optional LLM LoRA finetune on Modal ────────────────────────────
if ($Modal -and ($args -contains "--finetune-llm")) {
    Write-Host ""
    Write-Host "Launching Robinson LLM LoRA finetune on Modal..."
    & $Modal run finetune_llm_modal.py
} else {
    Write-Host ""
    Write-Host "LLM finetune ready. Launch with:"
    Write-Host "  .\run_eval_and_finetune.ps1 --finetune-llm"
    Write-Host "Or VITS resume finetune:"
    Write-Host "  `$env:VITS_RESTORE_PATH='/checkpoints/waxal_hausa_vits_v1/...'; .\train.ps1"
}

Write-Host ""
Write-Host "Eval complete. Review output_tests/*.wav and data/processed/robinson/sft_train.jsonl"
