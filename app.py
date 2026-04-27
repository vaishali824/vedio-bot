from flask import Flask, request, send_file, jsonify
import os
from gtts import gTTS
import subprocess

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

        # Save input video
        video_file = request.files["video"]
        video_path = "input.mp4"
        video_file.save(video_path)

        # Generate audio from text
        audio_path = "voice.mp3"
        tts = gTTS(text=script, lang="hi")
        tts.save(audio_path)

        # Output video
        output_path = "output.mp4"

        # Merge video + audio using ffmpeg
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

        return send_file(output_path, mimetype="video/mp4")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
