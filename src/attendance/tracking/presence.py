"""Presence tracking for a single class session.

Maintains an in-memory state of which students are currently present
and decides when to emit entry/exit events to the database. A student
who leaves and later returns during the same session produces a new
entry/exit pair, rather than being collapsed into "first seen / last
seen" — this is what allows the system to later calculate exactly how
long a student was absent, not just whether they were absent at some
point.
"""

from dataclasses import dataclass, field
from datetime import datetime

from attendance.db.queries import log_event
from attendance.config import MISSED_CHECKS_BEFORE_EXIT


@dataclass
class StudentTrackState:
    """In-memory presence state for a single student within a session."""
    is_present: bool = False
    missed_checks: int = 0


class PresenceTracker:
    """Tracks student presence during a live class session.

    Called once per recognition cycle (every
    ``RECOGNITION_INTERVAL_SECONDS``) with the set of students detected
    in that cycle. Emits an "entry" event the first time a student is
    seen, and an "exit" event after they go undetected for
    ``MISSED_CHECKS_BEFORE_EXIT`` consecutive cycles — this tolerance
    avoids treating a single missed detection (e.g. someone briefly
    turning away from the camera) as an actual absence.
    """

    def __init__(self, engine, session_id: int):
        self._engine = engine
        self._session_id = session_id
        self._states: dict[str, StudentTrackState] = {}

    def process_detected_students(self, detected_student_ids: set[str]) -> None:
        """Update presence state based on one recognition cycle's results.

        Args:
            detected_student_ids: Set of student IDs identified in the
                current cycle.
        """
        now = datetime.utcnow()

        for student_id in detected_student_ids:
            state = self._states.setdefault(student_id, StudentTrackState())
            state.missed_checks = 0

            if not state.is_present:
                state.is_present = True
                log_event(self._engine, self._session_id, student_id, "entry")

        for student_id, state in self._states.items():
            if student_id in detected_student_ids:
                continue
            if not state.is_present:
                continue

            state.missed_checks += 1
            if state.missed_checks >= MISSED_CHECKS_BEFORE_EXIT:
                state.is_present = False
                log_event(self._engine, self._session_id, student_id, "exit")

    def finalize_session(self) -> None:
        """Close out any students still marked present when the class ends.

        Ensures every "entry" event has a matching "exit" event, so
        that later duration calculations never encounter an
        unterminated presence interval.
        """
        for student_id, state in self._states.items():
            if state.is_present:
                log_event(self._engine, self._session_id, student_id, "exit")
                state.is_present = False