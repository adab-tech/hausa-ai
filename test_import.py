import modal

app = modal.App("test-import")

test_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "libsndfile1", "espeak-ng", "ffmpeg", "build-essential", "python3-dev")
    .pip_install(
        "coqui-tts==0.22.1",
        "torch==2.1.2",
        "torchaudio==2.1.2",
    )
)

@app.function(image=test_image)
def inspect_tts():
    import inspect
    import TTS.tts.datasets as d
    print("=== _get_formatter_by_name source ===")
    print(inspect.getsource(d._get_formatter_by_name))
    print("=== load_tts_samples source ===")
    print(inspect.getsource(d.load_tts_samples))

@app.local_entrypoint()
def main():
    inspect_tts.remote()
