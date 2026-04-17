import typing
from pathlib import Path
from uuid import uuid4

import whisper
from fastapi import FastAPI, Request, UploadFile
from sympy.unify.core import unify_var

from db import SvaraDB
import llm

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

    items = db_instance.get_items()

    items_str = "\n".join(
        f"Item name:{item.name} Item ID:{item.item_id}" for item in items
    )

    llm_response = llm.process_request(text, room_nr, items_str)
    # {
    #     "items": [
    #         {
    #             "item_id": 1,
    #             "item_name": "Bath Towel",
    #             "amount": 2,
    #             "room_nr": "204",
    #             "text_as_notes": "2 Bath Towels to room 204"
    #         }
    #     ],
    #     "unavailable_items": []
    # }

    unavailable_items = []
    added_items = []

    for item in llm_response.get("items", []):
        is_possible = db_instance.is_item_available(item["item_id"],item["amount"])
        if not is_possible:
            unavailable_items.append({
                "item" : item,
                "reason": "There are not enough of this item in the room."
            })
        added_items.append(item)
        await db_instance.add_request(
            int(room_nr),
            item["item_id"],
            item["amount"],
            item["text_as_notes"],
        )

    unavailable_items.extend(
        [{"item": item, "reason": "Item isn't available"} for item in llm_response.get("unavailable_items", [])]
    )

    return {
        "items": added_items,
        "unavailable_items": unavailable_items,
    }, 200


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
