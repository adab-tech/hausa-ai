# Google Colab VITS Resuming Guide

This guide details the exact steps to transition and resume the training of your custom **VITS Multi-Speaker Hausa TTS model** from Step 10,000 to completion (1,000 epochs) using Google Colab's GPU accelerators.

---

## Prerequisites

1.  **Google Account:** Access to [Google Colab](https://colab.research.google.com).
2.  **GCP Authentication:** Ensure the account has permission to read and write to your GCS bucket:
    `gs://hausa-ai-waxal-studio-980910821-5b814`

---

## Step-by-Step Execution

Create a new notebook in Google Colab, set the runtime to **T4 GPU** (Runtime -> Change runtime type -> T4 GPU), and execute the following cells.

### Cell 1: Authenticate with Google Cloud
This cell grants Google Colab permission to read the audio dataset and write checkpoints back to your GCS bucket.

```python
from google.colab import auth
auth.authenticate_user()
print("Authenticated successfully!")
```

### Cell 2: Install Base System Dependencies
Install CUDA-enabled PyTorch (default in Colab), Google Cloud Storage client, and the Coqui TTS framework.

```bash
# Install GCP storage client
!pip install google-cloud-storage

# Install Coqui TTS and its dependencies
!pip install coqui-tts
```

### Cell 3: Sync Datasets & Checkpoints (Bypassing Private Repository Clone)
Since the repository is private, you do not need to authenticate GitHub in Colab. Simply **drag-and-drop** the file `utils/prepare_colab_env.py` from your local computer directly into Google Colab's **Files tab** (click the folder icon on the left sidebar of Colab). 

Once uploaded, run the cell below to sync the dataset manifests, download all 1,572 audio files locally, and fetch all existing checkpoints from GCS:

```bash
# Run the synced script
!python prepare_colab_env.py
```

### Cell 4: Launch Training (with Custom Formatter)
Because our VITS configuration uses a custom dataset formatter (`waxal_hausa`), running the standard `train_tts` command directly will fail to parse the data. 

Instead, we run the orchestration script `run_train_tts.py` (which is automatically downloaded from your GCS checkpoints directory to the `checkpoints/` folder). Run the cell below to resume training from Step 10,000:

```bash
# Run training using the synced orchestration script
!python checkpoints/waxal_hausa_vits_v1-*/run_train_tts.py
```

### Cell 5: Sync New Checkpoints Back to GCS (Do Not Skip)
If your Colab session is about to time out, or if you decide to pause training manually, run the cell below to upload all newly generated checkpoints (e.g. Step 12,000, 14,000, etc.) back to your GCS bucket. This ensures you never lose a single step of progress.

```bash
# Sync local checkpoints back to GCS
!gsutil -m rsync -r checkpoints gs://hausa-ai-waxal-studio-980910821-5b814/checkpoints
print("Checkpoints successfully synced back to GCS!")
```

---

## Core Training Parameters

*   **Sample Rate:** 24,000 Hz (High-Fidelity)
*   **Active Speakers:** 8 (Google WAXAL multi-speaker subset)
*   **Characters/Alphabet:** Hooked letters (`ɓ`, `ɗ`, `ƙ`, `ƴ`) and pitch melody accent markers (`́`, `̀`).
*   **Target Epochs:** 1,000 epochs (approx. 388,000 steps).
*   **Resuming Step:** 10,000+ (Epoch 25+).
