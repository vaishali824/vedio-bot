from flask import Flask, request, send_file, jsonify
import os
import requests
from gtts import gTTS
import subprocess
import tempfile
import uuid
import traceback

app = Flask(__name__)

# FIXED: correct way to use environment variable
PEXELS_API_KEY = os.environ.get("TXUuyk5yBjVYtB34k33VInB2gjbhnjI0DGmd5RwaU3H2rp1JYbtETY4c", "")


def download_pexels_video(keyword: str, output_path: str):
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        params = {
            "query": keyword,
            "per_page": 3,
            "orientation": "portrait"
        }
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params=params,
            timeout=30
        )
        data = response.json()
        videos = data.get("videos", [])
        if not videos:
            return False

        video_files = sorted(
            videos[0]["video_files"],
            key=lambda x: x.get("width", 9999)
        )

        video_url = video_files[0]["link"]

        r = requests.get(video_url, stream=True, timeout=60)
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        return True

    except Exception as e:
        print(f"Pexels error: {e}")
        return False


def combine_video_audio(video_path, audio_path, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", video_path,
        "-i", audio_path,
        "-shortest",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-r", "30",
        "-movflags", "+faststart",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise Exception(f"FFmpeg error: {result.stderr}")

    return output_path


@app.route("/generate", methods=["POST"])
def generate_video():
    try:
        data = request.get_json(force=True, silent=True)
        print(f"Received: {data}")

        if not data:
            return jsonify({"error": "No data received"}), 400

        script = str(data.get("script", ""))
        topic = str(data.get("topic", "health tips"))

        if not script:
            return jsonify({"error": "No script"}), 400

        tmpdir = tempfile.mkdtemp()
        uid = str(uuid.uuid4())[:8]

        audio_path = os.path.join(tmpdir, f"audio_{uid}.mp3")
        video_path = os.path.join(tmpdir, f"video_{uid}.mp4")
        output_path = os.path.join(tmpdir, f"final_{uid}.mp4")

        # AUDIO
        tts = gTTS(text=script, lang='hi')
        tts.save(audio_path)

        # VIDEO
        success = download_pexels_video(topic, video_path)

        if not success:
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "color=c=black:s=1080x1920:r=30",
                "-t", "60",
                video_path
            ], capture_output=True, timeout=60)

        # MERGE
        combine_video_audio(video_path, audio_path, output_path)

        return send_file(
            output_path,
            mimetype="video/mp4",
            as_attachment=True,
            download_name="health_video.mp4"
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running"})


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "message": "Hindi Health Video Bot!"
    })
