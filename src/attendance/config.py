from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # raíz del proyecto
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "attendance.db"

DATABASE_URL = f"sqlite:///{DB_PATH}"

# --- Recognition / tracking tuning ---
RECOGNITION_INTERVAL_SECONDS = 18       # cada cuánto corre el modelo
MISSED_CHECKS_BEFORE_EXIT = 3           # revisiones seguidas sin ver a alguien -> "exit"

MATCH_THRESHOLD = 0.45

