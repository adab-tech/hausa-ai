"""Prepare the Railway volume, then drop privileges before running Murya."""

import os
from pathlib import Path


def main():
    volume = Path("/app/review-data")
    if os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") == str(volume):
        data = volume / "db"
        data.mkdir(mode=0o700, exist_ok=True)
        os.chown(data, 10001, 10001)

    os.setgroups([])
    os.setgid(10001)
    os.setuid(10001)
    os.execvp("uvicorn", ["uvicorn", "voice_preview:app", "--host", "0.0.0.0", "--port", os.environ.get("PORT", "8000")])


if __name__ == "__main__":
    main()
