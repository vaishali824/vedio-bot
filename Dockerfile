FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg libgl1 && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN pip install --upgrade pip

# Copy requirements
COPY requirements.txt .

# Install Python packages (force install)
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir moviepy

# Copy all files
COPY . .

# Run app
CMD ["python", "app.py"]
