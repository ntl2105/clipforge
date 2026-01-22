#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/download_output.sh <run_id> [local_out_dir]
#
# Example:
#   ./scripts/download_output.sh run_20260122_113012 audio_private/out

AWS_REGION="${AWS_REGION:-eu-west-1}"
BUCKET="${BUCKET:-video-highlights-jade-123}"
PREFIX="${PREFIX:-clipforge}"

RUN_ID="${1:-}"
LOCAL_OUT="${2:-audio_private/out}"

if [[ -z "$RUN_ID" ]]; then
  echo "Usage: $0 <run_id> [local_out_dir]"
  exit 1
fi

mkdir -p "$LOCAL_OUT/$RUN_ID"

S3_OUT="s3://${BUCKET}/${PREFIX}/outputs/${RUN_ID}/"

echo "Downloading from: $S3_OUT"
echo "To:              $LOCAL_OUT/$RUN_ID"
aws s3 cp "$S3_OUT" "$LOCAL_OUT/$RUN_ID" --recursive --region "$AWS_REGION"

echo "✅ Downloaded."
echo "Local: $LOCAL_OUT/$RUN_ID"