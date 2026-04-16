import typing
from pathlib import Path
from uuid import uuid4

import whisper
from fastapi import FastAPI, UploadFile

model = whisper.load_model("base")
app = FastAPI(title="SVARA Room Service API")

# app.include_router(requests_router, prefix="/api/requests", tags=["requests"])
# app.include_router(inventory_router, prefix="/api/inventory", tags=["inventory"])
# app.include_router(reports_router, prefix="/api/reports", tags=["reports"])
# app.include_router(reconciliations_router, prefix="/api/reconciliations", tags=["reconciliations"])
# app.include_router(ws_router, tags=["websocket"])


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/requests")
def new_request(): ...


@app.get("/api/requests")
def get_requests(): ...


@app.get("/api/requests/room/<room>")
def get_requests_by_room(room: str): ...


@app.patch("/api/requests/<request_id>")
def update_request(request_id: str): ...


@app.post("/api/voice_to_text")
def voice_to_text(files: UploadFile) -> dict[str, str | list[typing.Any]]:
    filename = files.filename or f"{uuid4().hex}.mp3"

    file = Path("tmp") / filename
    file.parent.mkdir(exist_ok=True)
    with file.open("wb") as buffer:
        buffer.write(files.file.read())
    try:
        return model.transcribe(audio=file.as_posix())
    except Exception as e:
        return {"error": str(e)}
    finally:
        file.unlink()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
