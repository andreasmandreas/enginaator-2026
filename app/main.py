import typing
from pathlib import Path
from uuid import uuid4

import whisper
from fastapi import FastAPI, Request, UploadFile

from db import SvaraDB

model = whisper.load_model("base")
app = FastAPI(title="SVARA Room Service API")
db_instance = SvaraDB("svara", "svara", "iamstupid123", "172.28.61.160")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/new_request")
async def new_request(request: Request) -> tuple[dict[str, typing.Any], int]:
    room_nr = request.query_params.get("room_nr")
    if not room_nr:
        return {"error": "Missing room_nr"}, 400

    data = await request.body()
    if not data:
        return {"error": "Missing audio file."}, 400

    file = Path("tmp", mkdir_exist_ok=True).joinpath(f"{uuid4().hex}.webm")
    try:
        with file.open("wb") as buffer:
            buffer.write(data)

    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}, 500

    finally:
        file.unlink()

    text = model.transcribe(file.as_posix())

    # TODO feed into LLM
    {"text": text, "room_nr": room_nr, "items": ...}  # noqa: B018
    return None


@app.get("/api/all_requests")
async def get_requests() -> list[Request]:
    return await db_instance.get_requests()


@app.get("/api/requests/room/<room>")
def get_requests_by_room(room: str) -> None: ...


@app.put("/api/requests/<request_id>")
async def update_request(request: Request, request_id: str) -> None:
    eta = (await request.json()).get("eta")
    if eta:
        int(eta)
    status = (await request.json()).get("status")
    if status:
        status = status.upper()

    await db_instance.update_request(
        int(request_id),
        eta if eta else None,
        status if status else None,
    )


def voice_to_text(files: UploadFile) -> dict[str, str | list[typing.Any]]:
    filename = files.filename or f"{uuid4().hex}.mp3"

    file = Path("tmp") / filename
    file.parent.mkdir(exist_ok=True)
    with file.open("wb") as buffer:
        buffer.write(files.file.read())
    try:
        return model.transcribe(audio=file.as_posix())
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
    finally:
        file.unlink()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
