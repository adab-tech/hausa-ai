import os
import sys
import argparse
from pathlib import Path

def download_from_gcs(bucket_name, dest_dir):
    """
    Downloads the WAXAL dataset manifests and audio files from GCS
    to the local dest_dir.
    """
    try:
        from google.cloud import storage
    except ImportError:
        print("Error: 'google-cloud-storage' is not installed. Please run: pip install google-cloud-storage")
        sys.exit(1)

    print(f"Connecting to GCS Bucket: gs://{bucket_name}...")
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
    except Exception as e:
        print(f"Authentication error: {e}")
        print("Please ensure you are authenticated by running: gcloud auth application-default login")
        sys.exit(1)

    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)
    audio_dir = dest_path / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    # 1. Download manifests and config files from GCS root
    manifest_files = ["metadata_processed.jsonl", "tts_filelist.txt", "config.json"]
    print("\n--- Downloading Manifests and Configurations ---")
    for filename in manifest_files:
        blob = bucket.blob(filename)
        if blob.exists():
            local_file = dest_path / filename
            print(f"Downloading {filename} -> {local_file}...")
            blob.download_to_filename(str(local_file))
        else:
            print(f"Manifest '{filename}' not found in bucket. Skipping.")

    # 2. Download all audio files under audio/ prefix
    print("\n--- Syncing Audio Files (this may take a few minutes) ---")
    blobs = bucket.list_blobs(prefix="audio/")
    count = 0
    
    for blob in blobs:
        if blob.name.endswith("/"): # Skip folders/prefixes
            continue
            
        # Determine local path
        relative_path = blob.name  # e.g. "audio/Hausa_M1_001_0080.mp3"
        local_file = dest_path / relative_path
        
        # Ensure parent directory exists (e.g. if audio/ subfolders exist)
        local_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not local_file.exists():
            print(f"Downloading {relative_path}...")
            blob.download_to_filename(str(local_file))
            count += 1
        else:
            # Skip if already exists
            pass

    print(f"\nSuccessfully downloaded {count} new audio files into {audio_dir}.")
    print("Dataset preparation is complete and ready for VITS training!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download dataset from GCS for training.")
    parser.add_argument("--bucket", type=str, default="hausa-ai-waxal-studio-980910821-5b814", help="GCS bucket name")
    parser.add_argument("--data-dir", type=str, default="waxal_hausa", help="Target local directory")
    args = parser.parse_args()
    
    download_from_gcs(args.bucket, args.data_dir)
