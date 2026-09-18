"""Database engine creation and initialization.

Configures the SQLAlchemy engine for SQLite with WAL (Write-Ahead
Logging) mode enabled, which allows the camera worker process to write
attendance events while the Streamlit dashboard reads concurrently
without blocking either process.
"""

from sqlalchemy import create_engine, event

from attendance.config import DATABASE_URL
from attendance.db.schema import metadata


def get_engine():
    """Create a SQLAlchemy engine configured for concurrent local access.

    Enables WAL mode (so readers and writers don't block each other)
    and enforces foreign key constraints, which SQLite does not do by
    default.

    Returns:
        A configured SQLAlchemy Engine instance.
    """
    engine = create_engine(DATABASE_URL, echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def init_db(engine):
    """Create all tables defined in the schema if they don't already exist.

    Args:
        engine: SQLAlchemy engine to create the tables on.
    """
    metadata.create_all(engine)