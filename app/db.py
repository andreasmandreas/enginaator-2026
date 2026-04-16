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
    amount: int = 1

    text: str

    room_nr: int
    status: str
    eta_minutes: int

    created_at: str
    updated_at: str


class SvaraDB:
    db_name: str
    db_user: str
    db_password: str

    def __init__(self, db_name: str, db_user: str, db_password: str):
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password

    async def __aenter__(self) -> psycopg.Connection:
        # TODO logging
        self._connection = psycopg.connect(
            dbname=self.db_name, user=self.db_user, password=self.db_password
        )
        return self._connection

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is not None:
            # TODO logging
            self._connection.rollback()
        else:
            # TODO logging
            self._connection.commit()
        self._connection.close()
        self._connection = None

    async def get_items(self) -> list[InventoryItem]:
        async with self as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM inventory_item")
            return [InventoryItem(**row) for row in cursor.fetchall()]

    async def add_request(self,room_nr: int, item_id: int, item_amount: int, text: str):
        async with self as connection:
            cursor = connection.cursor()

    async def update_request(self, request_id: int, status: str, eta_minutes: int):
        async with self as connection:
            cursor = connection.cursor()
            if status and eta_minutes:
                cursor.execute(
                    "UPDATE request SET status=%s, eta_minutes=%s WHERE request_id=%s",
                    (status, eta_minutes, request_id),
                )
            elif status:
                cursor.execute("UPDATE request SET status=%s WHERE request_id=%s", (status, request_id))
            elif eta_minutes:
                cursor.execute("UPDATE request SET eta_minutes=%s WHERE request_id=%s", (eta_minutes, request_id))
            else:
                raise ValueError("At least one of status or eta_minutes must be provided.")

    # TODO
    # queries
