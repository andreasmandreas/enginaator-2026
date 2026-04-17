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
    db_name: str
    db_user: str
    db_password: str

    def __init__(
        self,
        db_name: str,
        db_user: str,
        db_password: str,
        remote_addr: str = "localhost",
    ) -> None:
        self._working_table = None
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.remote_addr = remote_addr

    def table(self, table_name: str) -> typing.Self:
        self._working_table = table_name
        return self

    async def __aenter__(self) -> psycopg.Connection:
        # TODO logging
        self._connection = psycopg.connect(
            f"host={self.remote_addr} "
            f"dbname={self.db_name} "
            f"user={self.db_user} "
            f"password={self.db_password}",
        )
        return self._connection

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:  # noqa: ANN001
        if exc_type is not None:
            # TODO logging
            self._connection.rollback()
        else:
            # TODO logging
            self._connection.commit()
        self._working_table = None
        self._connection.close()
        self._connection = None

    async def get_items(self) -> list[InventoryItem]:
        async with self as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM inventory_items")
            return [
                InventoryItem(
                    item_id=row[0],
                    name=row[1],
                    category=row[2],
                    unit=row[3],
                    quantity_in_stock=row[4],
                    quantity_reserved=row[5],
                    quantity_available=row[6],
                    low_stock_threshold=row[7],
                )
                for row in cursor.fetchall()
            ]

    async def add_request(
        self,
        room_nr: int,
        item_id: int,
        item_amount: int,
        text: str,
    ) -> None:
        async with self.table("requests") as connection:
            cursor = connection.cursor()
            cursor.execute(
                """INSERT INTO requests (room, item_id, amount, notes)
                   VALUES (%s, %s, %s, %s)
                   RETURNING request_id;""",
                (room_nr, item_id, item_amount, text),
            )

    async def update_request(
        self,
        request_id: int,
        status: str | None = None,
        eta_minutes: int | None = None,
    ) -> None:
        async with self as connection:
            cursor = connection.cursor()
            if status and eta_minutes:
                cursor.execute(
                    "UPDATE requests SET status=%s, eta_minutes=%s WHERE request_id=%s",
                    (status, eta_minutes, request_id),
                )
            elif status:
                cursor.execute(
                    "UPDATE requests SET status=%s WHERE request_id=%s",
                    (status, request_id),
                )
            elif eta_minutes:
                cursor.execute(
                    "UPDATE requests SET eta_minutes=%s WHERE request_id=%s",
                    (eta_minutes, request_id),
                )
            else:
                msg = "At least one of status or eta_minutes must be provided."
                raise ValueError(
                    msg,
                )

    async def is_item_available(self, item_id: int, amount: int) -> bool:
        async with self as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                           SELECT 1
                           FROM inventory_items
                           WHERE item_id = %s
                             AND quantity_available >= %s
                           """,
                (item_id, amount),
            )

            return cursor.fetchone() is not None

    async def get_requests(self) -> list[Request]:
        async with self as connection:
            cursor = connection.cursor()
            requests = cursor.execute("""SELECT * FROM requests""").fetchall()
        return [
            Request(
                request_id=x[0],
                room_nr=x[1],
                item_id=x[2],
                amount=x[3],
                status=x[4],
                notes=x[5],
                eta_minutes=x[6],
                created_at=x[7],
                updated_at=x[8],
            )
            for x in requests
        ]

    async def get_room_request(self, room_nr: int | str) -> list[Request]:
        async with self as connection:
            cursor = connection.cursor()
            requests = cursor.execute(
                """SELECT * FROM requests WHERE room = %s""",
                (room_nr,),
            ).fetchall()
        return [
            Request(
                request_id=x[0],
                room_nr=x[1],
                item_id=x[2],
                amount=x[3],
                status=x[4],
                notes=x[5],
                eta_minutes=x[6],
                created_at=x[7],
                updated_at=x[8],
            )
            for x in requests
        ]

    # TODO
    # queries
