# Google Colab VITS Resuming Guide (Via Google Drive)

This guide outlines how to resume training your custom **VITS Multi-Speaker Hausa TTS model** using your **Google One (Google Drive)** storage and Colab's GPU accelerators, completely bypassing GCP billing.

---

## Prerequisites

1.  **Zip the Dataset:** Compress the local `waxal_hausa` folder on your computer to a zip file named `waxal_hausa.zip`:
    *   **Windows (File Explorer - Recommended):** Right-click the `waxal_hausa` folder in your file manager -> select **Send to** -> click **Compressed (zipped) folder**. This will create `waxal_hausa.zip` automatically.
    *   **Windows (PowerShell):**
        ```powershell
        Compress-Archive -Path waxal_hausa -DestinationPath waxal_hausa.zip
        ```
    *   **Linux/Mac:**
        ```bash
        tar -czf waxal_hausa.zip waxal_hausa
        ```
2.  **Upload to Google Drive:** Upload the resulting `waxal_hausa.zip` (~900MB) directly to your Google Drive home directory (`MyDrive/`).

---

## Step-by-Step Execution in Google Colab

Open a new notebook in Google Colab, change your runtime type to **T4 GPU** (Runtime -> Change runtime type -> T4 GPU), and execute the following cells.

### Cell 1: Mount Google Drive
This cell connects your Google Colab instance to your Google Drive account, enabling storage integration.

```python
from google.colab import drive
drive.mount('/content/drive')
```

### Cell 2: Install System Dependencies
Install the required packages, including PyTorch (pre-installed on Colab) and the Coqui TTS framework.

```bash
# Install Coqui TTS and its dependencies
!pip install coqui-tts
```

### Cell 3: Drag-and-drop Setup Script
Drag-and-drop the local file [prepare_drive_env.py](file:///c:/Users/Adamu/Desktop/hausa-ai-main/utils/prepare_drive_env.py) from your computer's `utils/` directory directly into Google Colab's **Files tab** (click the folder icon on the left sidebar of Colab). 

Once uploaded, run the cell below to extract the dataset locally (for maximum NVMe read speed) and symlink your checkpoints directory directly to Google Drive (for real-time, persistent saves):

```bash
# Prepare the local and Drive environment
!python prepare_drive_env.py
```

### Cell 4: Launch Training
Run the cell below to start or resume the training. Because the checkpoints directory is symlinked to your Google Drive, Coqui TTS will automatically detect your GCS-synced checkpoints (e.g., `checkpoint_10000.pth`) and continue training from **Step 10,000+**. Every new checkpoint generated will be saved directly into Google Drive in real-time.

```bash
# Run training using the synced orchestration script
!python run_train_tts.py --config_path waxal_hausa/config.json
```

---

## Advantages of this Workflow
*   **Zero GCP Cost:** Avoids all active virtual machine and storage fees on Google Cloud.
*   **Performance:** Audio files are read directly from Colab's local NVMe disk (`/content/waxal_hausa/`), maintaining maximum step speeds (~0.1s/step).
*   **Robust Persistence:** Checkpoints are written directly to Google Drive, ensuring that even if your Colab session times out, **you lose zero data**.
