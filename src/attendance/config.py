"""Central configuration for the attendance system.

Defines file system paths, database connection settings, and tunable
constants used across the recognition, tracking, and reporting modules.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "attendance.db"
INSTITUTIONAL_PHOTOS_DIR = DATA_DIR / "institutional_photos"

DATABASE_URL = f"sqlite:///{DB_PATH}"

# --- Recognition / tracking tuning ---

# How often (in seconds) the worker runs face recognition on a new frame.
# Kept intentionally low-frequency to avoid saturating the CPU on
# consumer laptops, since attendance tracking does not require
# per-frame analysis.
RECOGNITION_INTERVAL_SECONDS = 18

# Number of consecutive recognition cycles a student must be undetected
# before the system marks them as having exited (rather than reacting
# to a single missed detection, which could be a false negative).
MISSED_CHECKS_BEFORE_EXIT = 3

# Minimum cosine similarity for a face embedding to be considered a
# match against a known student. Tuned empirically: same-person pairs
# scored ~0.73, different-person pairs scored ~-0.02 in testing.
MATCH_THRESHOLD = 0.45

# --- Color palette (dark theme) ---

COLOR_BACKGROUND = "#0E0E1A"
COLOR_CARD = "#1E1B3A"
COLOR_PRIMARY = "#8B5CF6"
COLOR_SECONDARY = "#6D28D9"
COLOR_ACCENT = "#2DD4BF"
COLOR_TEXT = "#F5F5F7"
COLOR_TEXT_MUTED = "#A1A1AA"

PLOTLY_COLOR_SEQUENCE = [COLOR_PRIMARY, COLOR_ACCENT, COLOR_SECONDARY, "#F472B6", "#FBBF24"]