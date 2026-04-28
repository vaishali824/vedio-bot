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


# ---------- SAFE TTS GENERATION ----------
def generate_audio(script, audio_path):
    for i in range(5):
        try:
            print(f"TTS attempt {i+1}")

            # remove old/broken file
            if os.path.exists(audio_path):
                os.remove(audio_path)

            tts = gTTS(text=script, lang='hi')
            tts.save(audio_path)

            # check file size (important)
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
                raise Exception("Audio corrupted or too small")

            print("Audio generated successfully")
            return True

        except Exception as e:
            print("TTS ERROR:", e)
            time.sleep(20)

    return False


# ---------- DOWNLOAD VIDEO ----------
def download_pexels_video(keyword, output_path):
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

        print("Video downloaded")
        return True

    except Exception as e:
        print("Pexels error:", e)
        return False


# ---------- MERGE ----------
def combine_video_audio(video_path, audio_path, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", video_path,
        "-i", audio_path,
        "-shortest",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,"
               "pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-r", "30",
        "-movflags", "+faststart",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise Exception(result.stderr)

    print("Video merged successfully")


# ---------- MAIN API ----------
@app.route("/generate", methods=["POST"])
def generate_video():
    try:
        print("STEP 1: Request received")

        data = request.get_json(force=True, silent=True)

        if not data:
            return jsonify({"error": "No data received"}), 400

        script = str(data.get("script", ""))
        topic = str(data.get("topic", "health"))

        if not script:
            return jsonify({"error": "No script"}), 400

        tmpdir = tempfile.mkdtemp()
        uid = str(uuid.uuid4())[:8]

        audio_path = os.path.join(tmpdir, f"audio_{uid}.mp3")
        video_path = os.path.join(tmpdir, f"video_{uid}.mp4")
        output_path = os.path.join(tmpdir, f"final_{uid}.mp4")

        # ---------- AUDIO ----------
        print("STEP 2: Generating audio")
        success = generate_audio(script, audio_path)

        if not success:
            return jsonify({"error": "TTS failed (rate limit)"}), 429

        # safety check
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
            return jsonify({"error": "Invalid audio file"}), 500

        # ---------- VIDEO ----------
        print("STEP 3: Downloading video")
        success = download_pexels_video(topic, video_path)

        if not success:
            print("Using fallback video")
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "color=c=black:s=1080x1920:r=30",
                "-t", "60",
                video_path
            ], capture_output=True, timeout=60)

        # ---------- MERGE ----------
        print("STEP 4: Merging video")
        combine_video_audio(video_path, audio_path, output_path)

        print("STEP 5: Sending output")

        return send_file(
            output_path,
            mimetype="video/mp4",
            as_attachment=True,
            download_name="video.mp4"
        )

    except Exception as e:
        print("MAIN ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------- HEALTH ----------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running"})


# ---------- HOME ----------
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "running", "message": "Video API working"})
