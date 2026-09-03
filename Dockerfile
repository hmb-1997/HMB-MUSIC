FROM python:3.11-slim

# دابەزاندنا FFmpeg و هەمی پێدڤیێن دەنگی و سیستەمی
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libffi-dev \
    libsodium-dev \
    libopus-dev \
    build-essential \
    python3-dev

WORKDIR /app

# کۆپی کرنا فایلێن پێدڤی
COPY requirements.txt .

# دامەزراندنا کتێبخانەیان
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# دەستپێکرنا بۆتی
CMD ["python", "main.py"]
