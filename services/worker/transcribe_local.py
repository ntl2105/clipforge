import argparse
import json
import subprocess
from pathlib import Path

from faster_whisper import WhisperModel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", "-i", dest="inp", type=Path, required=True, help="Input audio file")
    parser.add_argument("--out", "-o", dest="out", type=Path, default=None, help="Output JSON path (default: same dir as input, transcript.json)")
    args = parser.parse_args()

    inp = args.inp.resolve()
    if not inp.exists():
        raise SystemExit(f"Input file not found: {inp}")

    parent = inp.parent
    stem = inp.stem
    wav = parent / f"{stem}.wav"
    out = args.out.resolve() if args.out else parent / "transcript.json"

    subprocess.run(["ffmpeg", "-y", "-i", str(inp), str(wav)], check=True)

    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(wav))

    data = {
        "source": {"local_path": str(inp)},
        "language": info.language,
        "model": "base",
        "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in segments],
    }

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", out)


if __name__ == "__main__":
    main()
