FROM python:3.11-slim

# دابەزاندنا FFmpeg ل سەر Railway
RUN apt-get update && apt-get install -y ffmpeg libffi-dev libsodium-dev build-essential

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
