from attendance.db.connection import get_engine, init_db

if __name__ == "__main__":
    engine = get_engine()
    init_db(engine)
    print("Database initialized.")
