# Hausa AI — Modal GPU Training Guide

> [!IMPORTANT]
> **Superseded (2026-07-06).** This guide covers the from-scratch Coqui-VITS
> approach, retired after native-speaker evaluation judged the output
> robotic. Its model files (`models/vits/`,
> `waxal_hausa_vits_v1-June-05-2026...`) have been deleted (~9.9 GB). The
> production voice is the **WAXAL–Piper grapheme-mode fine-tune** — see
> `docs/waxal_piper_technical_report.md` and `utils/run_training.ps1`. Kept
> for historical reference only.

This guide explains how to train your custom **WAXAL Hausa Multi-Speaker VITS** model serverlessly on the cloud using **Modal** and your free $30 credit.

---

## Prerequisites

1. **Modal Account:** Ensure you have signed up at [modal.com](https://modal.com) (they provide $30/month of free compute credits).
2. **Python Environment:** Use your local virtual environment where Python is installed.

---

## Step 1: Install and Set Up Modal

Open your terminal (PowerShell or Command Prompt) and run:

```bash
# 1. Install the modal CLI client
pip install modal

# 2. Authenticate the CLI with your Modal account (opens a browser window)
modal setup
```

---

## Step 2: Kick off Training on Modal

Once authenticated, you can trigger the training run on a remote serverless GPU (A10G) by executing the following command in the root of your project:

```bash
modal run train_modal.py
```

### What happens behind the scenes?
1. **Container Build:** Modal automatically builds a slim Debian container equipped with CUDA-enabled PyTorch and Coqui-TTS.
2. **Data Upload:** The local dataset folder (`waxal_hausa`) is mounted and uploaded automatically (~100-150MB).
3. **GPU Allocation:** A serverless NVIDIA A10G GPU is allocated.
4. **Custom Formatter:** The script parses filenames to assign proper speaker IDs (e.g. `M1`-`M4`, `F1`-`F4`).
5. **Prosody Tracking:** Hooked characters and high/low tone markers are loaded into the vocabulary.
6. **Continuous Sync:** Checkpoints are saved dynamically to a persistent Modal Volume (`hausa-ai-checkpoints`).

---

## Step 3: Monitoring & Lifecycle

- You can monitor the training logs directly in your terminal or via the **Modal Dashboard** link printed in your terminal.
- Since it runs serverlessly in the cloud, you can close your local terminal, and the training will continue running in the background!
- To view training runs or stop them manually, go to [dashboard.modal.com](https://dashboard.modal.com).

---

## Step 4: Retrieving Checkpoints

Once training has progressed (e.g., after a few hundred epochs or when validation loss stabilizes), you can download the checkpoints directly from the Modal Volume:

```bash
# List checkpoints stored in the persistent volume
modal volume ls hausa-ai-checkpoints

# Download the best checkpoint and config.json to your local models folder
modal volume get hausa-ai-checkpoints waxal_hausa_vits_v1/ models/vits/
```

After downloading:
1. Make sure your exported model has `best_model.onnx` (or convert the `.pth` checkpoint using the export roadmap).
2. Move it to `models/vits/` along with the `config.json` to load it in the FastAPI backend!
