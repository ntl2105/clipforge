# ClipForge

MVP pipeline:
S3 upload -> worker transcribes -> transcript.json in S3 -> (next) LLM highlights -> (next) ffmpeg render clips.