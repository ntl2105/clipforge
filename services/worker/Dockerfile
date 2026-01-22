FROM python:3.11-slim

# OS deps: ffmpeg for audio extraction/conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY transcribe_job.py .

# Default command (can be overridden)
CMD ["python3", "transcribe_job.py"]
