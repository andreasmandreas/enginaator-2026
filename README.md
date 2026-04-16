# enginaator-2026

# Minimal Flask + Whisper API

## Endpoint

POST `/api/whisper`

Form-data:
- `audio`: audio file (webm/wav/mp3/etc)
- `language`: (optional) language code (e.g. `en`, `es`, `fr`)

Returns JSON:
```
{
	"ok": true,
	"text": "...transcription...",
	"language": "en",
	"language_probability": 0.99
}
```

## Requirements
- Python 3.10+
- ffmpeg on PATH
- `pip install flask faster-whisper`

