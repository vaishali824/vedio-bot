from flask import Flask, request, jsonify, send_file
import asyncio
import os
import requests
import edge_tts
from moviepy.editor import (
    VideoFileClip, AudioFileClip,
    ImageClip, concatenate_videoclips,
    CompositeVideoClip, TextClip
)
from PIL import Image
import tempfile
import json

app = Flask(__name__)

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

# ─────────────────────────────────────────
# 1. Hindi Text-to-Speech (FREE)
# ─────────────────────────────────────────
async def generate_hindi_voice(script: str, output_path: str):
    communicate = edge_tts.Communicate(
        script,
        voice="hi-IN-MadhurNeural",  # Best Hindi male voice
        rate="+5%",                   # Slightly faster
        pitch="+0Hz"
    )
    await communicate.save(output_path)


# ─────────────────────────────────────────
# 2. Get Temple Videos from Pexels (FREE)
# ─────────────────────────────────────────
def download_temple_videos(topic: str, output_dir: str, count: int = 4):
    search_terms = [
        f"{topic} temple",
        "ancient temple india",
        "hindu temple architecture",
        "temple prayer spiritual"
    ]

    video_paths = []
    headers = {"Authorization": PEXELS_API_KEY}

    for i, term in enumerate(search_terms[:count]):
        try:
            url = "https://api.pexels.com/videos/search"
            params = {
                "query": term,
                "per_page": 1,
                "orientation": "portrait",
                "size": "medium"
            }
            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            videos = data.get("videos", [])
            if not videos:
                continue

            # Get smallest video file
            video_files = sorted(
                videos[0]["video_files"],
                key=lambda x: x.get("width", 9999)
            )
            video_url = video_files[0]["link"]

            video_path = os.path.join(output_dir, f"clip_{i}.mp4")
            r = requests.get(video_url, stream=True, timeout=30)
            with open(video_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            video_paths.append(video_path)
            print(f"✅ Downloaded clip {i+1}")

        except Exception as e:
            print(f"⚠️ Clip {i} failed: {e}")
            continue

    return video_paths


# ─────────────────────────────────────────
# 3. Build Final Video (1080x1920 Shorts)
# ─────────────────────────────────────────
def build_video(video_paths: list, audio_path: str, title: str, output_path: str):
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    print(f"🎵 Audio duration: {total_duration:.1f} seconds")

    clips = []
    accumulated = 0.0

    for vpath in video_paths:
        if accumulated >= total_duration:
            break
        try:
            clip = VideoFileClip(vpath).without_audio()

            # Resize to 1080x1920 (YouTube Shorts)
            clip = clip.resize(height=1920)
            if clip.w > 1080:
                x_center = clip.w / 2
                clip = clip.crop(
                    x1=x_center - 540,
                    x2=x_center + 540
                )
            elif clip.w < 1080:
                clip = clip.resize(width=1080)

            remaining = total_duration - accumulated
            if clip.duration > remaining:
                clip = clip.subclip(0, remaining)

            clips.append(clip)
            accumulated += clip.duration
            print(f"✅ Added clip: {accumulated:.1f}s / {total_duration:.1f}s")

        except Exception as e:
            print(f"⚠️ Clip error: {e}")
            continue

    if not clips:
        raise ValueError("No valid video clips!")

    # Concatenate all clips
    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.set_audio(audio)
    final_video = final_video.subclip(0, min(total_duration, final_video.duration))

    # Write final video
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=output_path + "_temp.m4a",
        remove_temp=True,
        logger=None,
        threads=4
    )

    # Cleanup
    for clip in clips:
        clip.close()
    audio.close()
    final_video.close()

    return output_path


# ─────────────────────────────────────────
# 4. Main API Endpoint (n8n calls this)
# ─────────────────────────────────────────
@app.route("/generate", methods=["POST"])
def generate_video():
    try:
        data = request.get_json()
        script = data.get("script", "")
        topic  = data.get("topic", "temple")
        title  = data.get("title", "Hindi Temple Story")

        if not script:
            return jsonify({"error": "No script provided"}), 400

        print(f"\n🛕 Starting video for: {topic}")

        # Create temp working directory
        tmpdir = tempfile.mkdtemp()
        audio_path  = os.path.join(tmpdir, "voice.mp3")
        output_path = os.path.join(tmpdir, "final.mp4")

        # Step 1 – Hindi Voiceover
        print("🎙️ Generating Hindi voiceover...")
        asyncio.run(generate_hindi_voice(script, audio_path))
        print("✅ Voiceover done!")

        # Step 2 – Download Temple Videos
        print("🎬 Downloading temple videos from Pexels...")
        video_paths = download_temple_videos(
            topic=topic,
            output_dir=tmpdir,
            count=4
        )
        print(f"✅ Downloaded {len(video_paths)} clips!")

        # Step 3 – Build Video
        print("🎞️ Building final video...")
        build_video(video_paths, audio_path, title, output_path)
        print("✅ Video ready!")

        # Return video file directly
        return send_file(
            output_path,
            mimetype="video/mp4",
            as_attachment=True,
            download_name="temple_video.mp4"
        )

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────
# 5. Health Check
# ─────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "✅ Hindi Temple Bot Running!"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting Hindi Temple Video Bot on port {port}")
    app.run(host="0.0.0.0", port=port)
