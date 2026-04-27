from flask import Flask, request, send_file, jsonify
import os
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip

app = Flask(__name__)

# -------------------------
# Basic routes (keep them)
# -------------------------
@app.route("/")
def home():
    return jsonify({"status": "running", "message": "Temple Bot is Live!"})

@app.route("/health")
def health():
    return jsonify({"status": "running"})


# -------------------------
# NEW: Merge API
# -------------------------
@app.route("/merge", methods=["POST"])
def merge_video_audio():
    try:
        # 🔹 Get script
        script = request.form.get("script")
        if not script:
            return jsonify({"error": "Script missing"}), 400

        # 🔹 Get video file
        if "video" not in request.files:
            return jsonify({"error": "Video file missing"}), 400

        video_file = request.files["video"]
        video_path = "input.mp4"
        video_file.save(video_path)

        # 🔹 Generate Hindi audio
        audio_path = "voice.mp3"
        tts = gTTS(text=script, lang="hi")
        tts.save(audio_path)

        # 🔹 Load video + audio
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)

        # 🔹 Match duration
        audio = audio.set_duration(video.duration)

        # 🔹 Merge
        final = video.set_audio(audio)

        output_path = "output.mp4"
        final.write_videofile(output_path, codec="libx264", audio_codec="aac")

        # 🔹 Return video
        return send_file(output_path, mimetype="video/mp4")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------
# OLD route (optional)
# -------------------------
@app.route("/generate", methods=["POST", "GET"])
def generate():
    return jsonify({"status": "deprecated", "message": "Use /merge endpoint"})


# -------------------------
# Run app
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
