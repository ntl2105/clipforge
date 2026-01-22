#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

def run(cmd):
    subprocess.run(cmd, check=True)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True, help="Path to original audio (m4a/wav)")
    p.add_argument("--highlights", required=True, help="Path to highlights JSON")
    p.add_argument("--out", help="Output file (wav or m4a). Default: audio_files/out/highlight_reel.wav")
    p.add_argument("--tmpdir", default="audio_files/rendered_clips", help="Where to store intermediate clips")
    args = p.parse_args()

    audio = Path(args.audio).resolve()
    highlights_path = Path(args.highlights).resolve()
    if args.out:
        out = Path(args.out)
    else:
        out = Path("audio_files/out") / "highlight_reel.wav"
    out = out.resolve()
    tmpdir = Path(args.tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)

    data = json.loads(highlights_path.read_text(encoding="utf-8"))
    highs = data["highlights"]

    clip_paths = []
    for i, h in enumerate(highs):
        start = float(h["start"])
        end = float(h["end"])
        dur = max(0.0, end - start)

        clip = tmpdir / f"clip_{i:02d}.wav"
        clip_paths.append(clip)

        # Accurate-ish cutting: use -ss/-t with re-encode to wav
        run([
            "ffmpeg", "-y",
            "-ss", f"{start:.3f}",
            "-t", f"{dur:.3f}",
            "-i", str(audio),
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "pcm_s16le",
            str(clip)
        ])

    # Build concat list file
    concat_list = tmpdir / "concat.txt"
    concat_list.write_text(
        "\n".join([f"file '{p.resolve()}'" for p in clip_paths]) + "\n",
        encoding="utf-8"
    )

    # Concatenate (wav -> wav)
    run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(out)
    ])

    print(f"✅ Wrote highlight reel to: {out}")

if __name__ == "__main__":
    main()