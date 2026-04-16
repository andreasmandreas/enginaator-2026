import typing

import psycopg

class SvaraDB:
    db_name: str
    db_user: str
    db_password: str

    def __init__(self,db_name: str,db_user: str,db_password: str):
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password

    def __aenter__(self) -> psycopg.Connection:
        # TODO logging
        self._connection = psycopg.connect(dbname=self.db_name, user=self.db_user, password=self.db_password)
        return self._connection

    def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is not None:
            # TODO logging
            self._connection.rollback()
        else:
            # TODO logging
            self._connection.commit()
        self._connection.close()
        self._connection = None

    # TODO
    # queries
