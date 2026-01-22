import json
import os
import subprocess
import sys
from pathlib import Path

import boto3
from faster_whisper import WhisperModel

AWS_REGION = os.environ.get("AWS_REGION", "eu-west-1")
BUCKET = os.environ.get("BUCKET")
MODEL_SIZE = os.environ.get("WHISPER_MODEL", "base")  # tiny/base/small...

def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def main():
    if not BUCKET:
        print("Missing BUCKET env var (e.g. BUCKET=video-highlights-jade-123)")
        sys.exit(1)

    if len(sys.argv) != 2:
        print("Usage: python3 transcribe_job.py <s3_key>")
        sys.exit(1)

    s3_key = sys.argv[1]
    job_id = s3_key.replace("/", "_").replace(".", "_")

    workdir = Path(f"/tmp/clipforge_{job_id}")
    workdir.mkdir(parents=True, exist_ok=True)

    local_in = workdir / Path(s3_key).name
    local_wav = workdir / "audio.wav"
    local_out = workdir / "transcript.json"

    s3 = boto3.client("s3", region_name=AWS_REGION)

    print(f"[1/4] Download s3://{BUCKET}/{s3_key}")
    s3.download_file(BUCKET, s3_key, str(local_in))

    print("[2/4] Convert to WAV (ffmpeg)")
    run(["ffmpeg", "-y", "-i", str(local_in), str(local_wav)])

    print(f"[3/4] Transcribe (faster-whisper: {MODEL_SIZE})")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(local_wav))

    out = {
        "s3_input": {"bucket": BUCKET, "key": s3_key},
        "language": info.language,
        "model": MODEL_SIZE,
        "segments": [
            {"start": s.start, "end": s.end, "text": s.text}
            for s in segments
        ],
    }

    with open(local_out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    out_key = f"jobs/{job_id}/transcript.json"
    print(f"[4/4] Upload transcript -> s3://{BUCKET}/{out_key}")
    s3.upload_file(str(local_out), BUCKET, out_key)

    print("DONE ✅")
    print("Output:", f"s3://{BUCKET}/{out_key}")

if __name__ == "__main__":
    main()
