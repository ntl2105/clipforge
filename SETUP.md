# ClipForge Infra Setup Log

## AWS Account
- Account ID: 688799538225
- CLI IAM user: jadapus
- Region: eu-west-1

## S3
- Bucket: video-highlights-jade-123
- Public access: blocked ✅
- Notes: created via console

## IAM
- `jadapus` policies:
  - AmazonS3FullAccess ✅
  - AmazonEC2FullAccess ✅
- EC2 worker role: clipforge-worker-role ✅
- EC2 role policy: clipforge-s3-policy ✅ (scoped to video-highlights-jade-123)

## EC2 Worker
- Instance Name tag: clipforge-worker
- Instance ID: TODO
- Instance type: c7i-flex.large
- Key pair (AWS): clipforge-worker-key
- Private key file: ~/clipforge-worker-key.pem
- Security Group ID: TODO
- Public IP: changes after stop/start (last seen: 54.74.84.216)
- SSH:
  ssh -i ~/clipforge-worker-key.pem ec2-user@<PUBLIC_IP>

### Installed on EC2
- docker ✅
- ffmpeg ✅ (static)
- python3 + pip ✅
- faster-whisper ✅

## Verified Working
- [x] AWS CLI works (sts get-caller-identity)
- [x] S3 upload/download works
- [x] EC2 SSH works
- [x] Docker works
- [x] ffmpeg works
- [x] faster-whisper works
- [x] EC2 role can access S3 (no access keys on box)
- [x] Worker Docker image builds successfully
- [x] Dockerized transcription works: docker run … clipforge-worker <s3_key>

## Docker
- Image name: clipforge-worker
- Build command:
  cd ~/clipforge/services/worker && docker build -t clipforge-worker .
- Run command:
  docker run --rm -e AWS_REGION=eu-west-1 -e BUCKET=video-highlights-jade-123 clipforge-worker test/sample.m4a