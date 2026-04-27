from flask import Flask, request, send_file, jsonify
import os
import requests
from gtts import gTTS
import subprocess
import tempfile
import uuid

app = Flask(__name__)

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

# ─────────────────────────────────────────
# 1. Generate Hindi Audio using gTTS (Google)
# ─────────────────────────────────────────
def generate_audio(script: str, output_path: str):
    tts = gTTS(text=script, lang='hi', slow=False)
    tts.save(output_path)
    print("✅ Audio generated!")


# ─────────────────────────────────────────
# 2. Download Video from Pexels
# ─────────────────────────────────────────
def download_pexels_video(keyword: str, output_path: str):
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": keyword,
        "per_page": 3,
        "orientation": "portrait"
    }
    try:
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params=params,
            timeout=30
        )
        data = response.json()
        videos = data.get("videos", [])

        if not videos:
            print("⚠️ No Pexels videos found!")
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
        print("✅ Video downloaded!")
        return True

    except Exception as e:
        print(f"❌ Pexels error: {e}")
        return False


# ─────────────────────────────────────────
# 3. Combine Video + Audio using FFmpeg
# ─────────────────────────────────────────
def combine_video_audio(video_path: str, audio_path: str, output_path: str):
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

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300
    )

    if result.returncode != 0:
        raise Exception(f"FFmpeg failed: {result.stderr}")

    print("✅ Video combined!")
    return output_path


# ─────────────────────────────────────────
# 4. Main Generate Endpoint
# ─────────────────────────────────────────
@app.route("/generate", methods=["POST"])
def generate_video():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data received"}), 400

        script = data.get("script", "")
        topic = data.get("topic", "health tips")
        title = data.get("title", "Health Tips")

        if not script:
            return jsonify({"error": "No script provided"}), 400

        print(f"\n🎬 Starting: {title}")

        tmpdir = tempfile.mkdtemp()
        unique_id = str(uuid.uuid4())[:8]
        audio_path = os.path.join(tmpdir, f"audio_{unique_id}.mp3")
        video_path = os.path.join(tmpdir, f"video_{unique_id}.mp4")
        output_path = os.path.join(tmpdir, f"final_{unique_id}.mp4")

        # Step 1 — Generate Hindi Audio
        print("🎙️ Generating Hindi audio...")
        generate_audio(script, audio_path)

        # Step 2 — Download Pexels Video
        print("🎬 Downloading video...")
        success = download_pexels_video(topic, video_path)

        if not success:
            print("⚠️ Using black fallback video...")
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "color=c=black:s=1080x1920:r=30",
                "-t", "60",
                video_path
            ], capture_output=True, timeout=60)

        # Step 3 — Combine with FFmpeg
        print("🎞️ Combining video + audio...")
        combine_video_audio(video_path, audio_path, output_path)

        print("✅ Video ready! Sending to n8n...")
        return send_file(
            output_path,
            mimetype="video/mp4",
            as_attachment=True,
            download_name="health_video.mp4"
        )

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────
# 5. Health Check
# ─────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "✅ Hindi Health Bot Running!"})


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "message": "Hindi Health Video Bot is Live!"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Starting on port {port}")
    app.run(host="0.0.0.0", port=port)
