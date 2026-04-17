# testing static files
import typing
from uuid import uuid4

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="SVARA Room Service API")

frontend_dir = Path(__file__).parent.parent / "public" / "src"
print(f"Looking for static files at: {frontend_dir.absolute()}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")

import whisper
from fastapi import FastAPI, UploadFile

model = whisper.load_model("base")

# app.include_router(requests_router, prefix="/api/requests", tags=["requests"])
# app.include_router(inventory_router, prefix="/api/inventory", tags=["inventory"])
# app.include_router(reports_router, prefix="/api/reports", tags=["reports"])
# app.include_router(reconciliations_router, prefix="/api/reconciliations", tags=["reconciliations"])
# app.include_router(ws_router, tags=["websocket"])


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/voice_to_text")
async def voice_to_text(files: UploadFile):
    contents = await files.read()

    suffix = Path(files.filename).suffix if files.filename else ".webm"
    filename = f"{uuid4().hex}{suffix}"

    file = Path("tmp") / filename
    file.parent.mkdir(exist_ok=True)

    with file.open("wb") as buffer:
        buffer.write(contents)

    try:
        return model.transcribe(audio=file.as_posix())
    except Exception as e:
        return {"error": str(e)}
    finally:
        file.unlink()

app.mount("/static", StaticFiles(directory=frontend_dir, html=True), name="static")

if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8000)
