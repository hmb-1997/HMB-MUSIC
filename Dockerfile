FROM python:3.11-slim

# دابەزاندنا هەمی پێدڤیێن دەنگی و سیستەمی
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus-dev \
    libffi-dev \
    libsodium-dev \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# دابەزاندنا کتێبخانەیێن پایتۆن
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# دەستپێکرنا بۆتی
CMD ["python", "main.py"]
