from flask import Flask, request, send_file, jsonify
from gtts import gTTS
import subprocess
import uuid
import os

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({"status": "running"})


@app.route("/merge", methods=["POST"])
def merge():
    try:
        script = request.form.get("script")

        if not script:
            return jsonify({"error": "No script provided"}), 400

        if "video" not in request.files:
            return jsonify({"error": "No video uploaded"}), 400

        # Unique file names (IMPORTANT for multiple requests)
        uid = str(uuid.uuid4())

        video_path = f"{uid}_input.mp4"
        audio_path = f"{uid}_voice.mp3"
        output_path = f"{uid}_output.mp4"

        # Save video
        video_file = request.files["video"]
        video_file.save(video_path)

        # Generate Hindi voice
        tts = gTTS(text=script, lang="hi")
        tts.save(audio_path)

        # FFmpeg merge command
        command = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]

        subprocess.run(command, check=True)

        # Send final video
        response = send_file(output_path, mimetype="video/mp4")

        # Cleanup (optional but important)
        os.remove(video_path)
        os.remove(audio_path)
        os.remove(output_path)

        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
