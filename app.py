from flask import Flask, request, send_file, jsonify
import os
import requests
from gtts import gTTS  # keep import (not used now, safe to remove later)
import subprocess
import tempfile
import uuid
import traceback

app = Flask(__name__)

PEXELS_API_KEY = os.environ.get("TXUuyk5yBjVYtB34k33VInB2gjbhnjI0DGmd5RwaU3H2rp1JYbtETY4c", "")

# ----------- FIXED TTS (NO gTTS LIMIT) -----------
def generate_audio(script, audio_path):
    try:
        script = script[:200]  # IMPORTANT limit

        url = "https://translate.google.com/translate_tts"
        params = {
            "ie": "UTF-8",
            "q": script,
            "tl": "hi",
            "client": "tw-ob"
        }
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        r = requests.get(url, params=params, headers=headers)

        if r.status_code != 200:
            raise Exception("TTS request failed")

        with open(audio_path, "wb") as f:
            f.write(r.content)

        if os.path.getsize(audio_path) < 1000:
            raise Exception("Audio too small")

        print("TTS OK")
        return True

    except Exception as e:
        print("TTS ERROR:", e)
        return False


# ----------- VIDEO DOWNLOAD -----------
def download_pexels_video(keyword: str, output_path: str):
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        params = {
            "query": keyword,
            "per_page": 1
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

        video_url = videos[0]["video_files"][0]["link"]

        r = requests.get(video_url, stream=True)

        with open(output_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

        print("Video OK")
        return True

    except Exception as e:
        print("Pexels error:", e)
        return False


# ----------- MERGE -----------
def combine_video_audio(video_path, audio_path, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", video_path,
        "-i", audio_path,
        "-shortest",
        "-c:v", "libx264",
        "-c:a", "aac",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(result.stderr)

    print("Merge OK")


# ----------- MAIN API -----------
@app.route("/generate", methods=["POST"])
def generate_video():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data"}), 400

        script = str(data.get("script", ""))
        topic = str(data.get("topic", "health"))

        if not script:
            return jsonify({"error": "No script"}), 400

        tmpdir = tempfile.mkdtemp()
        uid = str(uuid.uuid4())[:8]

        audio_path = os.path.join(tmpdir, f"audio_{uid}.mp3")
        video_path = os.path.join(tmpdir, f"video_{uid}.mp4")
        output_path = os.path.join(tmpdir, f"final_{uid}.mp4")

        # AUDIO
        print("Generating audio...")
        ok = generate_audio(script, audio_path)
        if not ok:
            return jsonify({"error": "TTS failed"}), 500

        # VIDEO
        print("Downloading video...")
        success = download_pexels_video(topic, video_path)

        if not success:
            print("Using fallback video...")
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "color=c=black:s=720x1280",
                "-t", "30",
                video_path
            ])

        # MERGE
        print("Merging...")
        combine_video_audio(video_path, audio_path, output_path)

        return send_file(output_path, mimetype="video/mp4")

    except Exception as e:
        print("MAIN ERROR:", e)
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


@app.route("/")
def home():
    return jsonify({"status": "running"})
