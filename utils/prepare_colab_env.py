import os
import sys
import concurrent.futures
from google.cloud import storage

PROJECT_ID = "studio-980910821-5b814"
BUCKET_NAME = "hausa-ai-waxal-studio-980910821-5b814"
DATA_DIR = "waxal_hausa"

def main():
    print("=" * 60)
    print("      HAUSA AI — GOOGLE COLAB ENVIRONMENT PREPARATOR        ")
    print("=" * 60)
    
    # Initialize GCS client
    try:
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(BUCKET_NAME)
        print(f"Authenticated successfully for project: {PROJECT_ID}")
    except Exception as auth_err:
        print(f"Failed to authenticate GCS client: {auth_err}")
        print("Make sure you run google.colab.auth.authenticate_user() first in Colab!")
        sys.exit(1)
        
    # 1. Download manifests
    print("\n[1] Downloading training manifests...")
    os.makedirs(DATA_DIR, exist_ok=True)
    for filename in ["metadata_processed.jsonl", "tts_filelist.txt"]:
        dest_path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(dest_path):
            blob = bucket.blob(filename)
            blob.download_to_filename(dest_path)
            print(f"  Downloaded: {filename}")
        else:
            print(f"  Already exists: {filename}")
            
    # 2. Download audio files in parallel
    print("\n[2] Syncing audio files locally (parallel download)...")
    audio_dir = os.path.join(DATA_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    
    blobs = list(client.list_blobs(BUCKET_NAME, prefix="audio/"))
    print(f"  Found {len(blobs)} audio files on GCS.")
    
    def download_audio_blob(blob):
        dest_path = os.path.join(DATA_DIR, blob.name)
        if not os.path.exists(dest_path):
            blob.download_to_filename(dest_path)
            
    # Run parallel downloader
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        executor.map(download_audio_blob, blobs)
    print("  Audio sync complete.")
    
    # 3. Sync existing checkpoints
    print("\n[3] Syncing existing checkpoints from GCS (for training resume)...")
    os.makedirs("checkpoints", exist_ok=True)
    
    checkpoint_blobs = list(client.list_blobs(BUCKET_NAME, prefix="checkpoints/"))
    print(f"  Found {len(checkpoint_blobs)} checkpoint artifacts on GCS.")
    
    def download_checkpoint_blob(blob):
        # blob.name will be like checkpoints/waxal_hausa_vits_v1-.../checkpoint_10000.pth
        local_path = blob.name
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        if not os.path.exists(local_path):
            blob.download_to_filename(local_path)
            print(f"    Synced: {os.path.basename(local_path)}")
            
    # Run checkpoint sync
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(download_checkpoint_blob, checkpoint_blobs)
    print("  Checkpoint sync complete.")
    
    print("\n" + "=" * 60)
    print("COLAB PREPARATION COMPLETE! Ready to run training.")
    print("Run this command next in Colab to resume training:")
    print("!python -m TTS.bin.train_tts --config_path waxal_hausa/config.json")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
