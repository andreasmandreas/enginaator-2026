from flask import Flask, request, jsonify
from faster_whisper import WhisperModel
import tempfile
import os

app = Flask(__name__)

model = WhisperModel("base", device="cpu", compute_type="int8")

@app.post("/api/whisper")
def api_whisper():
    if "audio" not in request.files:
        return jsonify({"ok": False, "error": "Missing audio file."}), 400
    audio_file = request.files["audio"]
    language = (request.form.get("language") or "").strip() or None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name
    try:
        segments, info = model.transcribe(
            tmp_path,
            language=language,
            vad_filter=True,
        )
        text = "".join(segment.text for segment in segments).strip()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
    return jsonify({
        "ok": True,
        "text": text,
        "language": info.language,
        "language_probability": info.language_probability,
    })

if __name__ == "__main__":
    app.run(host="localhost", port=5000)
