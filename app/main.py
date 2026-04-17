import typing
from pathlib import Path
from uuid import uuid4

import whisper
from fastapi import FastAPI, Request, UploadFile, WebSocket, WebSocketDisconnect
from db import SvaraDB
import llm

model = whisper.load_model("base")
app = FastAPI(title="SVARA Room Service API")
db_instance = SvaraDB("svara", "svara", "iamstupid123", "172.28.61.160")


# --- WEBSOCKET CONNECTION MANAGER ---
class ConnectionManager:
    def __init__(self):
        # Map room_nr to a list of active websocket connections
        self.active_rooms: dict[str, list[WebSocket]] = {}
        # List for staff dashboard connections
        self.staff_dashboards: list[WebSocket] = []

    async def connect_room(self, websocket: WebSocket, room_nr: str):
        await websocket.accept()
        if room_nr not in self.active_rooms:
            self.active_rooms[room_nr] = []
        self.active_rooms[room_nr].append(websocket)

    async def connect_staff(self, websocket: WebSocket):
        await websocket.accept()
        self.staff_dashboards.append(websocket)

    def disconnect_room(self, websocket: WebSocket, room_nr: str):
        if room_nr in self.active_rooms and websocket in self.active_rooms[room_nr]:
            self.active_rooms[room_nr].remove(websocket)

    def disconnect_staff(self, websocket: WebSocket):
        if websocket in self.staff_dashboards:
            self.staff_dashboards.remove(websocket)

    async def broadcast_to_room(self, room_nr: str, message: dict):
        if room_nr in self.active_rooms:
            for connection in self.active_rooms[room_nr]:
                await connection.send_json(message)

    async def broadcast_to_staff(self, message: dict):
        for connection in self.staff_dashboards:
            await connection.send_json(message)


manager = ConnectionManager()


# --- WEBSOCKET ROUTES ---
@app.websocket("/ws/guest/{room_nr}")
async def websocket_guest(websocket: WebSocket, room_nr: str):
    await manager.connect_room(websocket, room_nr)
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except WebSocketDisconnect:
        manager.disconnect_room(websocket, room_nr)


@app.websocket("/ws/staff")
async def websocket_staff(websocket: WebSocket):
    await manager.connect_staff(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except WebSocketDisconnect:
        manager.disconnect_staff(websocket)


# --- REST ENDPOINTS ---
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
        text = model.transcribe(file.as_posix())["text"]
    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        if file.exists():
            file.unlink()

    items = await db_instance.get_items()
    items_str = "\n".join(
        f"Item name:{item.name} Item ID:{item.item_id}" for item in items
    )
    llm_response = llm.process_request(text, room_nr, items_str)

    unavailable_items = []
    added_items = []

    for item in llm_response.get("items", []):
        # Attempt to add request & reserve stock atomically
        req_id = await db_instance.add_request(
            int(room_nr), item["item_id"], item["amount"], item["text_as_notes"]
        )

        if req_id is None:
            unavailable_items.append(
                {"item": item, "reason": "Not enough stock available."}
            )
        else:
            item["request_id"] = req_id
            added_items.append(item)

            # Broadcast the new request to the staff dashboard
            await manager.broadcast_to_staff(
                {"type": "NEW_REQUEST", "request": item, "room": room_nr}
            )
            # Confirm to the specific room's tablet
            await manager.broadcast_to_room(
                room_nr, {"type": "REQUEST_CONFIRMED", "request": item}
            )

    unavailable_items.extend(
        [
            {"item": item, "reason": "Item isn't available in catalog"}
            for item in llm_response.get("unavailable_items", [])
        ]
    )

    return {
        "items": added_items,
        "unavailable_items": unavailable_items,
        "transcript": text,
    }, 200


@app.get("/api/all_requests")
async def get_requests():
    return await db_instance.get_requests()


@app.get("/api/requests/room/{room}")
async def get_requests_by_room(room: str):
    return await db_instance.get_room_request(room)


@app.patch("/api/requests/{request_id}")
async def update_request(request: Request, request_id: str):
    body = await request.json()
    eta = body.get("eta")
    status = body.get("status")

    if status:
        status = status.upper()

    await db_instance.update_request(int(request_id), int(eta) if eta else None, status)

    # Fetch updated requests to broadcast
    all_requests = await db_instance.get_requests()
    updated_req = next(
        (r for r in all_requests if r.request_id == int(request_id)), None
    )

    if updated_req:
        # Route update event selectively to the specific room
        await manager.broadcast_to_room(
            str(updated_req.room_nr),
            {
                "type": "STATUS_UPDATE",
                "request_id": request_id,
                "status": status,
                "eta": eta,
            },
        )

        # Broadcast status change to staff
        await manager.broadcast_to_staff(
            {
                "type": "STATUS_UPDATE",
                "request_id": request_id,
                "status": status,
                "room": str(updated_req.room_nr),
            }
        )

    return {"message": "updated successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
