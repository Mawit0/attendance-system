# src/attendance/tracking/presence.py

from dataclasses import dataclass, field
from datetime import datetime
from attendance.db.queries import log_event
from attendance.config import MISSED_CHECKS_BEFORE_EXIT


@dataclass
class StudentTrackState:
    is_present: bool = False
    missed_checks: int = 0


class PresenceTracker:
    """
    Mantiene el estado en memoria de quién está presente durante una sesión,
    y decide cuándo generar eventos entry/exit hacia la base de datos.
    """

    def __init__(self, engine, session_id: int):
        self._engine = engine
        self._session_id = session_id
        self._states: dict[str, StudentTrackState] = {}

    def process_detected_students(self, detected_student_ids: set[str]) -> None:
        """
        Llamar una vez por cada ciclo de revisión (cada RECOGNITION_INTERVAL_SECONDS),
        con el set de matrículas detectadas en esa revisión.
        """
        now = datetime.utcnow()

        # Estudiantes detectados en esta revisión
        for student_id in detected_student_ids:
            state = self._states.setdefault(student_id, StudentTrackState())
            state.missed_checks = 0

            if not state.is_present:
                state.is_present = True
                log_event(self._engine, self._session_id, student_id, "entry")

        # Estudiantes NO detectados en esta revisión (de los que ya conocíamos)
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
        """
        Llamar al terminar la clase — cierra con 'exit' a cualquiera
        que siga marcado presente (para que todo intervalo entry tenga su exit).
        """
        for student_id, state in self._states.items():
            if state.is_present:
                log_event(self._engine, self._session_id, student_id, "exit")
                state.is_present = False
