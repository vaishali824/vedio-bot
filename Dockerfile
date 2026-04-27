FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg + system libs
RUN apt-get update && apt-get install -y ffmpeg libgl1 && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Run app
CMD ["python", "app.py"]
