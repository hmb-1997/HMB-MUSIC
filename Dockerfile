FROM python:3.11-slim

# دابەزاندنا FFmpeg و Node.js (بۆ yt-dlp یا فەرە)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    python3-dev \
    build-essential \
    libffi-dev \
    libsodium-dev \
    libopus-dev \
    && curl -sL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "main.py"]
