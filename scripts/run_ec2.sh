#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/run_ec2.sh s3://bucket/prefix/inputs/file.m4a [run_id]
#
# Example:
#   ./scripts/run_ec2.sh s3://video-highlights-jade-123/clipforge/inputs/call_ping.m4a

AWS_REGION="${AWS_REGION:-eu-west-1}"
BUCKET="${BUCKET:-video-highlights-jade-123}"
PREFIX="${PREFIX:-clipforge}"

S3_IN="${1:-}"
RUN_ID="${2:-}"

if [[ -z "$S3_IN" ]]; then
  echo "Usage: $0 <s3_input_uri> [run_id]"
  exit 1
fi

if [[ -z "$RUN_ID" ]]; then
  RUN_ID="run_$(date +%Y%m%d_%H%M%S)"
fi

WORKDIR="/home/ec2-user/tmp/clipforge/${RUN_ID}"
mkdir -p "$WORKDIR"

echo "Run ID:    $RUN_ID"
echo "Workdir:   $WORKDIR"
echo "Input:     $S3_IN"

# 1) Download input
aws s3 cp "$S3_IN" "$WORKDIR/input" --region "$AWS_REGION"

# 2) Run pipeline in Docker (mount workdir)
# Assumes image already built: clipforge-worker
docker run --rm \
  -v "$WORKDIR:/data" \
  -e AWS_REGION="$AWS_REGION" \
  -e BUCKET="$BUCKET" \
  clipforge-worker \
  python3 transcribe_local.py --in /data/input --out /data/transcript.json

docker run --rm \
  -v "$WORKDIR:/data" \
  clipforge-worker \
  python3 select_highlights.py --in /data/transcript.json --out /data/highlights.json

docker run --rm \
  -v "$WORKDIR:/data" \
  clipforge-worker \
  python3 render_highlights.py --audio /data/input --highlights /data/highlights.json --out /data/highlight_reel.wav

# 3) Upload outputs
S3_OUT="s3://${BUCKET}/${PREFIX}/outputs/${RUN_ID}/"
aws s3 cp "$WORKDIR/" "$S3_OUT" --recursive --region "$AWS_REGION"

echo "✅ Done."
echo "Outputs: $S3_OUT"