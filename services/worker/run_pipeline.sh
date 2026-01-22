#!/usr/bin/env bash
set -euo pipefail

AUDIO="$1"
OUTDIR="${2:-audio_files/out}"
mkdir -p "$OUTDIR"

TRANSCRIPT="$OUTDIR/transcript.json"
HIGHLIGHTS="$OUTDIR/highlights.json"
REEL="$OUTDIR/highlight_reel.wav"

# python services/worker/transcribe_local.py --in "$AUDIO" --out "$TRANSCRIPT"
# python services/worker/select_highlights.py --in "$TRANSCRIPT" --out "$HIGHLIGHTS"
python services/worker/render_highlights.py --audio "$AUDIO" --highlights "$HIGHLIGHTS" --out "$REEL"

echo "✅ Transcript: $TRANSCRIPT"
echo "✅ Highlights: $HIGHLIGHTS"
echo "✅ Reel: $REEL"
