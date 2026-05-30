import os
import sys
import shutil
import zipfile

DRIVE_ROOT = "/content/drive/MyDrive"
PROJECT_FOLDER = "hausa_ai_training"
LOCAL_DATA_DIR = "/content/waxal_hausa"
LOCAL_CHECKPOINTS_DIR = "/content/checkpoints"

def main():
    print("=" * 60)
    print("       HAUSA AI — GOOGLE DRIVE & COLAB SETUP ENGINE         ")
    print("=" * 60)
    
    # 1. Verify Google Drive mount
    drive_root = DRIVE_ROOT
    if not os.path.exists(drive_root):
        fallback_root = "/content/drive/My Drive"
        if os.path.exists(fallback_root):
            drive_root = fallback_root
        else:
            print("Error: Google Drive not found mounted at /content/drive/MyDrive or /content/drive/My Drive.")
            print("Please run the drive mount cell first in Colab:")
            print("  from google.colab import drive")
            print("  drive.mount('/content/drive')")
            sys.exit(1)
        
    drive_project_path = os.path.join(drive_root, PROJECT_FOLDER)
    drive_checkpoints_path = os.path.join(drive_project_path, "checkpoints")
    
    os.makedirs(drive_project_path, exist_ok=True)
    os.makedirs(drive_checkpoints_path, exist_ok=True)
    
    # 2. Check for zipped dataset in Google Drive
    # We look for waxal_hausa.zip in MyDrive or MyDrive/hausa_ai_training/
    zip_options = [
        os.path.join(drive_project_path, "waxal_hausa.zip"),
        os.path.join(drive_root, "waxal_hausa.zip")
    ]
    
    zip_source = None
    for path in zip_options:
        if os.path.exists(path):
            zip_source = path
            break
            
    if not zip_source:
        print("\n> [!WARNING]")
        print("> Could not find 'waxal_hausa.zip' on your Google Drive.")
        print(f"> Expected location: {zip_options[0]} or {zip_options[1]}")
        print("> Please zip your local 'waxal_hausa' folder on your computer:")
        print("    tar -czf waxal_hausa.zip waxal_hausa   (Linux/Mac)")
        print("    Compress-Archive -Path waxal_hausa -DestinationPath waxal_hausa.zip  (Windows PowerShell)")
        print("> Then, upload 'waxal_hausa.zip' directly to your Google Drive homepage or the 'hausa_ai_training' folder.")
        sys.exit(1)
        
    print(f"Found dataset archive: {zip_source}")
    
    # 3. Extract dataset locally on Colab's NVMe scratchpad (for high-speed training)
    if not os.path.exists(LOCAL_DATA_DIR):
        print(f"Extracting {zip_source} locally to {LOCAL_DATA_DIR}...")
        try:
            with zipfile.ZipFile(zip_source, "r") as zip_ref:
                # Extract to /content/ which handles the folder structure
                zip_ref.extractall("/content/")
            print("  Extraction completed successfully!")
        except Exception as e:
            print(f"Error during extraction: {e}")
            sys.exit(1)
    else:
        print(f"Dataset already exists locally at: {LOCAL_DATA_DIR}")
        
    # 4. Set up checkpoints symlink to Google Drive
    # This automatically streams checkpoints directly to Google Drive
    if os.path.exists(LOCAL_CHECKPOINTS_DIR):
        if os.path.islink(LOCAL_CHECKPOINTS_DIR):
            print(f"Checkpoints directory is already linked to Google Drive.")
        else:
            print(f"Warning: Local checkpoints directory exists but is not a link. Removing...")
            shutil.rmtree(LOCAL_CHECKPOINTS_DIR)
            os.symlink(drive_checkpoints_path, LOCAL_CHECKPOINTS_DIR)
            print(f"Created symlink: {LOCAL_CHECKPOINTS_DIR} -> {drive_checkpoints_path}")
    else:
        os.symlink(drive_checkpoints_path, LOCAL_CHECKPOINTS_DIR)
        print(f"Created symlink: {LOCAL_CHECKPOINTS_DIR} -> {drive_checkpoints_path}")
        
    # 5. Copy run_train_tts.py to root directory for easy access
    src_patch = "/content/waxal_hausa/checkpoints/waxal_hausa_vits_v1-May-26-2026_11+40AM-0000000/run_train_tts.py"
    if os.path.exists(src_patch):
        shutil.copy(src_patch, "/content/run_train_tts.py")
        print("Successfully copied run_train_tts.py to workspace root.")
    elif os.path.exists("/content/hausa-ai-main/utils/run_train_tts.py"):
        shutil.copy("/content/hausa-ai-main/utils/run_train_tts.py", "/content/run_train_tts.py")
        print("Successfully copied run_train_tts.py from cloned repo to root.")
        
    print("\n" + "=" * 60)
    print("COLAB DRIVE PREPARATION SUCCESSFUL!")
    print("To launch training, run this command in Colab:")
    print("  !python run_train_tts.py --config_path waxal_hausa/config.json")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
