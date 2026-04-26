from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "running", "message": "Temple Bot is Live!"})

@app.route("/health")
def health():
    return jsonify({"status": "running"})

@app.route("/generate", methods=["POST", "GET"])
def generate():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
