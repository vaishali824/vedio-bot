from flask import Flask, request, send_file, jsonify
import os
import requests
from gtts import gTTS
import subprocess
import tempfile
import uuid
import traceback
import time

app = Flask(__name__)

PEXELS_API_KEY = os.environ.get("TXUuyk5yBjVYtB34k33VInB2gjbhnjI0DGmd5RwaU3H2rp1JYbtETY4c", "")

# ------------------ TTS ------------------
def generate_audio(script, audio_path):
    for i in range(3):
        try:
            print(f"TTS attempt {i+1}")

            if os.path.exists(audio_path):
                os.remove(audio_path)

            tts = gTTS(text=script, lang='hi')
            tts.save(audio_path)

            # validate file
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
                raise Exception("Audio file corrupted")

            return True

        except Exception as e:
            print("TTS ERROR:", e)
            time.sleep(15)

    return False


# ------------------ VIDEO ------------------
def download_video(keyword, output_path):
    try:
        if not PEXELS_API_KEY:
            print("No API key, using fallback")
            return False

        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": keyword, "per_page": 1}

        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params=params,
            timeout=20
        )

        data = r.json()
        videos = data.get("videos", [])

        if not videos:
            return False

        video_url = videos[0]["video_files"][0]["link"]

        stream = requests.get(video_url, stream=True)

        with open(output_path, "wb") as f:
            for chunk in stream.iter_content(1024):
                f.write(chunk)

        return True

    except Exception as e:
        print("VIDEO ERROR:", e)
        return False


# ------------------ MERGE ------------------
def merge(video_path, audio_path, output_path):
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


# ------------------ API ------------------
@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON received"}), 400

        script = data.get("script")
        topic = data.get("topic", "health")

        if not script:
            return jsonify({"error": "No script"}), 400

        tmp = tempfile.mkdtemp()
        uid = str(uuid.uuid4())[:6]

        audio_path = os.path.join(tmp, f"a_{uid}.mp3")
        video_path = os.path.join(tmp, f"v_{uid}.mp4")
        output_path = os.path.join(tmp, f"o_{uid}.mp4")

        # ---- AUDIO ----
        ok = generate_audio(script, audio_path)
        if not ok:
            return jsonify({"error": "TTS failed"}), 500

        # ---- VIDEO ----
        ok = download_video(topic, video_path)
        if not ok:
            print("Using fallback video")
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "color=c=black:s=720x1280",
                "-t", "30",
                video_path
            ])

        # ---- MERGE ----
        merge(video_path, audio_path, output_path)

        return send_file(output_path, mimetype="video/mp4")

    except Exception as e:
        print("ERROR:", e)
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


# ------------------ HEALTH ------------------
@app.route("/")
def home():
    return jsonify({"status": "running"})


# ------------------ START ------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
