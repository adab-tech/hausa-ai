import os
import sys
import argparse
import json
import subprocess
from datasets import load_dataset, Audio

def main():
    parser = argparse.ArgumentParser(description="Pull Google's WAXAL Hausa speech dataset from Hugging Face and upload it to GCS.")
    parser.add_argument("--config", type=str, default="hau_tts", help="Dataset configuration (e.g. 'hau_tts')")
    parser.add_argument("--split", type=str, default="train", help="Dataset split (e.g. 'train')")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of samples to download (default: 10, set to 0 for unlimited)")
    parser.add_argument("--output-dir", type=str, default="waxal_hausa", help="Output directory to save audio and metadata locally")
    parser.add_argument("--bucket", type=str, default="hausa-ai-waxal-studio-980910821-5b814", help="GCS bucket name to upload data to")
    parser.add_argument("--upload", action="store_true", default=True, help="Enable uploading to GCS bucket after download")
    parser.add_argument("--project", type=str, default="studio-980910821-5b814", help="GCP project ID for bucket creation")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    audio_dir = os.path.join(args.output_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    print(f"Loading WAXAL dataset config='{args.config}', split='{args.split}' from Hugging Face...")
    try:
        dataset = load_dataset("google/WaxalNLP", name=args.config, split=args.split, streaming=True)
        # Disable audio decoding to get raw MP3 bytes directly, bypassing compiler-based decoders like torchcodec
        dataset = dataset.cast_column("audio", Audio(decode=False))
    except Exception as e:
        print(f"Error loading dataset: {e}")
        print("Please check the configuration name and network connection.")
        sys.exit(1)

    metadata = []
    count = 0

    print("Downloading and processing audio samples (as raw MP3 files)...")
    for idx, sample in enumerate(dataset):
        if args.limit > 0 and count >= args.limit:
            break

        sample_id = sample.get("id") or f"sample_{idx}"
        text = sample.get("text")
        speaker_id = sample.get("speaker_id", "unknown")
        gender = sample.get("gender", "unknown")
        audio_data = sample.get("audio")

        if not audio_data or "bytes" not in audio_data:
            print(f"Skipping sample {sample_id} due to missing audio bytes data.")
            continue

        raw_bytes = audio_data["bytes"]
        original_path = audio_data.get("path", "")
        
        # Determine output filename
        mp3_filename = os.path.basename(original_path) if original_path else f"{sample_id}.mp3"
        if not mp3_filename.endswith(".mp3"):
            mp3_filename += ".mp3"
            
        mp3_path = os.path.join(audio_dir, mp3_filename)
        
        try:
            with open(mp3_path, "wb") as f:
                f.write(raw_bytes)
        except Exception as write_err:
            print(f"Error saving MP3 file for {sample_id}: {write_err}")
            continue

        metadata.append({
            "id": sample_id,
            "speaker_id": speaker_id,
            "gender": gender,
            "text": text,
            "audio_file": f"audio/{mp3_filename}"
        })

        count += 1
        if count % 5 == 0:
            print(f"Processed {count} samples...")

    # Write metadata locally
    metadata_path = os.path.join(args.output_dir, "metadata.jsonl")
    with open(metadata_path, "w", encoding="utf-8") as f:
        for item in metadata:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\nSuccessfully downloaded {count} samples to local directory '{args.output_dir}'.")
    print(f"Metadata file written to: {metadata_path}")

    # Upload to Google Cloud Storage (GCS)
    if args.upload and count > 0:
        print(f"\n--- Staging data to Google Cloud Storage bucket: gs://{args.bucket} ---")
        
        # 1. Check if bucket exists
        print("Checking if GCS bucket exists...")
        check_bucket = subprocess.run(
            ["gcloud.cmd", "storage", "buckets", "describe", f"gs://{args.bucket}"],
            capture_output=True,
            text=True
        )
        
        # If bucket does not exist (describe command failed), create it
        if check_bucket.returncode != 0:
            print(f"Bucket gs://{args.bucket} does not exist. Creating it under project {args.project}...")
            create_bucket = subprocess.run(
                ["gcloud.cmd", "storage", "buckets", "create", f"gs://{args.bucket}", f"--project={args.project}", "--location=us-central1"],
                capture_output=True,
                text=True
            )
            
            if create_bucket.returncode == 0:
                print("GCS Bucket created successfully.")
            else:
                print(f"Failed to create bucket: {create_bucket.stderr}")
                sys.exit(1)
        else:
            print("GCS Bucket already exists.")

        # 2. Sync files to GCS
        print(f"Syncing local directory '{args.output_dir}' to gs://{args.bucket}...")
        sync_process = subprocess.run(
            ["gsutil.cmd", "-m", "rsync", "-r", args.output_dir, f"gs://{args.bucket}"],
            capture_output=True,
            text=True
        )
        
        if sync_process.returncode == 0:
            print("Successfully uploaded dataset to GCS!")
            print(f"Data is available in: gs://{args.bucket}")
        else:
            print(f"Upload failed: {sync_process.stderr}")

if __name__ == "__main__":
    main()
