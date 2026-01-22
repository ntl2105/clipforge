#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/upload_input.sh <local_audio_path> [name_without_ext]
#
# Example:
#   ./scripts/upload_input.sh audio_private/call_ping.m4a call_ping
# Load .env if it exists
if [[ -f ".env" ]]; then
  set -a
  source .env
  set +a
fi

AWS_REGION="${AWS_REGION:-eu-west-1}"
BUCKET="${BUCKET:-video-highlights-jade-123}"
PREFIX="${PREFIX:-clipforge}"

LOCAL_PATH="${1:-}"
NAME="${2:-}"

if [[ -z "$LOCAL_PATH" ]]; then
  echo "Usage: $0 <local_audio_path> [name_without_ext]"
  exit 1
fi

if [[ ! -f "$LOCAL_PATH" ]]; then
  echo "File not found: $LOCAL_PATH"
  exit 1
fi

FILENAME="$(basename "$LOCAL_PATH")"
EXT="${FILENAME##*.}"

if [[ -z "$NAME" ]]; then
  NAME="${FILENAME%.*}"
fi

S3_KEY="$PREFIX/inputs/${NAME}.${EXT}"
S3_URI="s3://${BUCKET}/${S3_KEY}"

echo "Uploading: $LOCAL_PATH"
echo "To:        $S3_URI"
aws s3 cp "$LOCAL_PATH" "$S3_URI" --region "$AWS_REGION"

echo "✅ Uploaded."
echo "S3_URI=$S3_URI"