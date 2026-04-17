import typing
import psycopg
from pydantic import BaseModel


class InventoryItem(BaseModel):
    item_id: int
    name: str
    category: str
    unit: str
    quantity_in_stock: int
    quantity_reserved: int
    quantity_available: int
    low_stock_threshold: int


class Request(BaseModel):
    request_id: int
    item_id: int
    amount: int
    notes: str
    room_nr: int
    status: str | None
    eta_minutes: int | None
    created_at: str
    updated_at: str


class SvaraDB:
    def __init__(
        self,
        db_name: str,
        db_user: str,
        db_password: str,
        remote_addr: str = "localhost",
    ) -> None:
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.remote_addr = remote_addr

    # Using psycopg 3 AsyncConnection for true async database operations
    async def get_connection(self):
        return await psycopg.AsyncConnection.connect(
            f"host={self.remote_addr} dbname={self.db_name} user={self.db_user} password={self.db_password}"
        )

    async def get_items(self) -> list[InventoryItem]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM inventory_items")
                rows = await cursor.fetchall()
                return [
                    InventoryItem(
                        item_id=r[0],
                        name=r[1],
                        category=r[2],
                        unit=r[3],
                        quantity_in_stock=r[4],
                        quantity_reserved=r[5],
                        quantity_available=r[6],
                        low_stock_threshold=r[7],
                    )
                    for r in rows
                ]

    async def add_request(
        self, room_nr: int, item_id: int, item_amount: int, text: str
    ) -> int | None:
        """Reserves stock atomically and creates the request."""
        async with await self.get_connection() as conn:
            async with conn.cursor() as cursor:
                # Start transaction to prevent race conditions
                await cursor.execute(
                    "SELECT quantity_available FROM inventory_items WHERE item_id = %s FOR UPDATE",
                    (item_id,),
                )
                res = await cursor.fetchone()

                if not res or res[0] < item_amount:
                    return None  # Not enough stock available

                # Reserve the stock
                await cursor.execute(
                    """
                                     UPDATE inventory_items
                                     SET quantity_reserved  = quantity_reserved + %s,
                                         quantity_available = quantity_available - %s
                                     WHERE item_id = %s
                                     """,
                    (item_amount, item_amount, item_id),
                )

                # Create the request
                await cursor.execute(
                    """
                                     INSERT INTO requests (room, item_id, amount, notes, status, created_at, updated_at)
                                     VALUES (%s, %s, %s, %s, 'RECEIVED', NOW(), NOW())
                                     RETURNING request_id;
                                     """,
                    (room_nr, item_id, item_amount, text),
                )

                req_id = (await cursor.fetchone())[0]
                await conn.commit()
                return req_id

    async def update_request(
        self, request_id: int, status: str | None = None, eta_minutes: int | None = None
    ) -> None:
        """Updates request and handles stock deduction on fulfillment or release on cancellation."""
        async with await self.get_connection() as conn:
            async with conn.cursor() as cursor:
                # Fetch current request info
                await cursor.execute(
                    "SELECT item_id, amount, status FROM requests WHERE request_id = %s FOR UPDATE",
                    (request_id,),
                )
                req = await cursor.fetchone()
                if not req:
                    raise ValueError("Request not found")

                item_id, amount, current_status = req

                # Deduct physical stock if delivered
                if status == "DELIVERED" and current_status != "DELIVERED":
                    await cursor.execute(
                        """
                                         UPDATE inventory_items
                                         SET quantity_in_stock = quantity_in_stock - %s,
                                             quantity_reserved = quantity_reserved - %s
                                         WHERE item_id = %s
                                         """,
                        (amount, amount, item_id),
                    )

                # Release reserved stock if rejected/cancelled
                elif status == "REJECTED" and current_status not in (
                    "REJECTED",
                    "DELIVERED",
                ):
                    await cursor.execute(
                        """
                                         UPDATE inventory_items
                                         SET quantity_reserved  = quantity_reserved - %s,
                                             quantity_available = quantity_available + %s
                                         WHERE item_id = %s
                                         """,
                        (amount, amount, item_id),
                    )

                # Update the request row
                if status and eta_minutes:
                    await cursor.execute(
                        "UPDATE requests SET status=%s, eta_minutes=%s, updated_at=NOW() WHERE request_id=%s",
                        (status, eta_minutes, request_id),
                    )
                elif status:
                    await cursor.execute(
                        "UPDATE requests SET status=%s, updated_at=NOW() WHERE request_id=%s",
                        (status, request_id),
                    )
                elif eta_minutes:
                    await cursor.execute(
                        "UPDATE requests SET eta_minutes=%s, updated_at=NOW() WHERE request_id=%s",
                        (eta_minutes, request_id),
                    )

                await conn.commit()

    async def get_requests(self) -> list[Request]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM requests ORDER BY created_at DESC")
                requests = await cursor.fetchall()
        return [
            Request(
                request_id=x[0],
                room_nr=x[1],
                item_id=x[2],
                amount=x[3],
                notes=x[4],
                status=x[5],
                eta_minutes=x[6],
                created_at=str(x[7]),
                updated_at=str(x[8]),
            )
            for x in requests
        ]

    async def get_room_request(self, room_nr: int | str) -> list[Request]:
        async with await self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM requests WHERE room = %s ORDER BY created_at DESC",
                    (room_nr,),
                )
                requests = await cursor.fetchall()
        return [
            Request(
                request_id=x[0],
                room_nr=x[1],
                item_id=x[2],
                amount=x[3],
                notes=x[4],
                status=x[5],
                eta_minutes=x[6],
                created_at=str(x[7]),
                updated_at=str(x[8]),
            )
            for x in requests
        ]
