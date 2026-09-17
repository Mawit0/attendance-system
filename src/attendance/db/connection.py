from sqlalchemy import create_engine, event
from attendance.config import DATABASE_URL
from attendance.db.schema import metadata


def get_engine():
    engine = create_engine(DATABASE_URL, echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine

def init_db(engine):
    metadata.create_all(engine)
