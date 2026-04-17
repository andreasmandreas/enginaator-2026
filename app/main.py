import typing
from pathlib import Path
from uuid import uuid4

import whisper
from fastapi import FastAPI, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from db import SvaraDB
import llm

try:
    model = whisper.load_model("base")
except Exception as e:
    print(f"Warning: Could not load Whisper model: {e}")
    model = None

app = FastAPI(title="SVARA Room Service API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dummy middleware to log requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"DEBUG: Request: {request.method} {request.url}")
    response = await call_next(request)
    print(f"DEBUG: Response: {response.status_code}")
    return response


db_instance = SvaraDB("svara", "svara", "iamstupid123", "172.28.61.160")


# --- WEBSOCKET CONNECTION MANAGER ---
class ConnectionManager:
    def __init__(self):
        # Map room_nr to a list of active websocket connections
        self.active_rooms: dict[str, list[WebSocket]] = {}
        # List for staff dashboard connections
        self.staff_dashboards: list[WebSocket] = []

    async def connect_room(self, websocket: WebSocket, room_nr: str):
        try:
            # We don't await accept() here anymore to let the route handler do it?
            # No, connect_room is called FROM the route handler.
            # Let's try to set a timeout for the handshake just in case.
            import asyncio

            print(f"DEBUG: Attempting to accept WS for room {room_nr}")
            await asyncio.wait_for(websocket.accept(), timeout=5.0)
            print(f"WS accepted for room: {room_nr}")
            if room_nr not in self.active_rooms:
                self.active_rooms[room_nr] = []
            self.active_rooms[room_nr].append(websocket)
        except asyncio.TimeoutError:
            print(f"DEBUG: Timeout during WS accept for room {room_nr}")
            return False
        except Exception as e:
            print(
                f"DEBUG: Exception during connect_room for {room_nr}: {type(e).__name__}: {e}"
            )
            return False
        return True

    async def connect_staff(self, websocket: WebSocket):
        try:
            await websocket.accept()
            print("WS accepted for staff")
            self.staff_dashboards.append(websocket)
        except Exception as e:
            print(f"Error accepting WS for staff: {e}")
            return False
        return True

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

# --- STATIC FILES ---
frontend_dir = Path(__file__).parent.parent / "public" / "src"


@app.get("/")
async def read_index():
    return FileResponse(frontend_dir / "index.html")


@app.get("/dashboard")
async def read_dashboard():
    return FileResponse(frontend_dir / "dashboard" / "index.html")


@app.get("/favicon.ico")
async def favicon():
    # Try to serve the icon from assets/imgs if it exists
    icon_path = frontend_dir / "assets" / "imgs" / "hotel_trivago.png"
    if icon_path.exists():
        return FileResponse(icon_path)
    return {"status": "no favicon"}


app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


# --- WEBSOCKET ROUTES ---
@app.websocket("/ws/guest/{room_nr}")
async def websocket_guest(websocket: WebSocket, room_nr: str):
    print(f"WS guest connection request: {room_nr}")
    connected = await manager.connect_room(websocket, room_nr)
    if not connected:
        return

    try:
        while True:
            # We must await receive_text or similar to keep the connection open
            # and detect when it closes.
            data = await websocket.receive_text()
            print(f"Received from room {room_nr}: {data}")
    except WebSocketDisconnect:
        print(f"WS guest disconnected: {room_nr}")
    except Exception as e:
        print(f"WS error for room {room_nr}: {e}")
    finally:
        manager.disconnect_room(websocket, room_nr)


@app.websocket("/ws/staff")
async def websocket_staff(websocket: WebSocket):
    print("WS staff connection request")
    connected = await manager.connect_staff(websocket)
    if not connected:
        return

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received from staff: {data}")
    except WebSocketDisconnect:
        print("WS staff disconnected")
    except Exception as e:
        print(f"WS error for staff: {e}")
    finally:
        manager.disconnect_staff(websocket)


# --- REST ENDPOINTS ---
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/new_request")
async def new_request(request: Request):
    room_nr = request.query_params.get("room_nr")
    if not room_nr:
        return {"error": "Missing room_nr"}

    data = await request.body()
    if not data:
        return {"error": "Missing audio file."}

    file = Path("tmp").joinpath(f"{uuid4().hex}.webm")
    try:
        if not model:
            return {"error": "Whisper model not loaded"}
        with file.open("wb") as buffer:
            buffer.write(data)
        text = model.transcribe(file.as_posix())["text"]
    except Exception as e:
        return {"error": str(e)}
    finally:
        if file.exists():
            file.unlink()

    items = await db_instance.get_items()
    items_str = "\n".join(f"Item name:{item.name} Item ID:{item.id}" for item in items)
    llm_response = llm.process_request(text, room_nr, items_str)

    unavailable_items = []
    added_items = []

    for item in llm_response.get("items", []):
        # Attempt to add request & reserve stock atomically
        req_id = await db_instance.add_request(
            room_nr, item["item_id"], item["amount"], item["text_as_notes"]
        )

        if req_id is None:
            unavailable_items.append(
                {"item": item, "reason": "Not enough stock available."}
            )
        else:
            item["id"] = req_id
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
    }


@app.get("/api/all_requests")
async def get_requests():
    return await db_instance.get_requests()


@app.get("/api/requests/room/{room}")
async def get_requests_by_room(room: str):
    return await db_instance.get_room_request(room)


@app.get("/api/inventory")
async def get_inventory():
    return await db_instance.get_items()


@app.post("/api/inventory/{item_id}/restock")
async def restock_item(item_id: int):
    await db_instance.restock_item(item_id)
    # Broadcast inventory update
    await manager.broadcast_to_staff({"type": "INVENTORY_UPDATE"})
    return {"message": "restocked successfully"}


@app.patch("/api/requests/{request_id}")
async def update_request(request: Request, request_id: str):
    body = await request.json()
    eta = body.get("eta")
    request_status = body.get("status")

    if request_status:
        request_status = request_status.upper()

    await db_instance.update_request(
        int(request_id), request_status, int(eta) if eta else None
    )

    # Fetch updated requests to broadcast
    all_requests = await db_instance.get_requests()
    updated_req = next((r for r in all_requests if r.id == int(request_id)), None)

    if updated_req:
        # Route update event selectively to the specific room
        await manager.broadcast_to_room(
            str(updated_req.room),
            {
                "type": "STATUS_UPDATE",
                "id": request_id,
                "request_status": request_status,
                "eta": eta,
            },
        )

        # Broadcast status change to staff
        await manager.broadcast_to_staff(
            {
                "type": "STATUS_UPDATE",
                "id": request_id,
                "request_status": request_status,
                "room": str(updated_req.room),
            }
        )

    return {"message": "updated successfully"}


if __name__ == "__main__":
    import uvicorn
    import sys
    import asyncio

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run(app, host="127.0.0.1", port=1488)
