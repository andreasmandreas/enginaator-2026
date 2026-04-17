
# enginaator-2026

Voice-driven hotel room service system with:
- FastAPI backend (room service API, inventory, requests, WebSocket for real-time updates)
- Whisper/OpenAI LLM integration for speech-to-structured-request
- Modern web frontend for guests and staff (dashboard, login, assets)

---

## Features

- Guests submit room service requests by voice (browser → backend)
- Speech-to-text (Whisper) and LLM extract structured requests
- Inventory and request management (add, update, restock, status)
- Real-time updates for staff dashboard and guest tablets via WebSocket

---

## Project Structure

- `app/` — FastAPI backend (main.py, db.py, llm.py, run.py)
- `public/src/` — Frontend (index.html, dashboard, login, assets)
- `public/src/assets/` — CSS, JS, images, fonts
- `pyproject.toml` — Python dependencies
- `CHANGES.md` — Changelog and team

---

## Setup

1. **Python 3.10+** (see `pyproject.toml` for dependencies)
2. **Install dependencies:**
   - `pip install -r requirements.txt` or use `uv`/`poetry`/`pip` as preferred
3. **ffmpeg** must be on your PATH for Whisper
4. **.env file:** Place LMS_KEY, LMS_MODEL, LMS_ENDPOINT in `app/.env`

---

## Running the App

**Development:**

```bash
cd app
python run.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 1488
```

**Frontend:**
- Open `public/src/index.html` (guest)
- Open `public/src/dashboard/index.html` (staff)

---

## API Endpoints (main ones)

### Health
- `GET /api/health` — Health check

### Room Service Request (voice)
- `POST /api/new_request` — Accepts audio, room_nr; returns structured items

### Inventory
- `GET /api/inventory` — List inventory items
- `POST /api/inventory/{item_id}/restock` — Restock item

### Requests
- `GET /api/all_requests` — All requests
- `GET /api/requests/room/{room}` — Requests for a room
- `PATCH /api/requests/{request_id}` — Update status/ETA

### WebSocket
- `/ws/guest/{room_nr}` — Guest tablet connection
- `/ws/staff` — Staff dashboard connection

---

## Code Quality & Contribution

- Follows PEP8, clear naming, minimal comments, docstrings for all public APIs
- See [CHANGES.md](CHANGES.md) for team and changelog

---

## License

AGPL-3.0 

