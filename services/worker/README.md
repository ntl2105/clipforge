# ClipForge Worker

Build:
docker build -t clipforge-worker .

Run:
docker run --rm \
  -e AWS_REGION=eu-west-1 \
  -e BUCKET=video-highlights-jade-123 \
  clipforge-worker test/sample.m4a
