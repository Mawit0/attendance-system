# scripts/seed_dummy_history.py
"""
Genera datos históricos de asistencia simulados para demostración.
NO usa la cámara ni los modelos de ML — inserta sesiones y eventos
directamente en la base de datos con patrones de asistencia realistas.
"""

import random
from datetime import datetime, timedelta

from attendance.db.connection import get_engine
from attendance.db.queries import get_students_by_group, start_session, end_session, log_event

GROUP_ID = 1  # 9A
NUM_SESSIONS = 10
SESSION_DURATION_MINUTES = 90
DAYS_BETWEEN_SESSIONS = 3

# Perfiles de asistencia por estudiante — para variedad realista.
# La clave es el índice del estudiante en la lista (orden alfabético
# de get_students_by_group), el valor es la probabilidad de asistir
# a cualquier sesión dada.
ATTENDANCE_PROFILES = {
    "excellent": 0.95,
    "good": 0.85,
    "average": 0.70,
    "at_risk": 0.45,
}


def assign_profiles(students):
    """Asigna un perfil de asistencia a cada estudiante, mezclado."""
    profiles = (
        ["excellent"] * 4 +
        ["good"] * 4 +
        ["average"] * 3 +
        ["at_risk"] * 2
    )
    random.shuffle(profiles)
    return {s.id: profiles[i % len(profiles)] for i, s in enumerate(students)}


def simulate_session(engine, group_id, session_date, students, profile_map):
    from sqlalchemy import insert, update
    from attendance.db.schema import class_sessions, attendance_events

    started_at = session_date
    ended_at = started_at + timedelta(minutes=SESSION_DURATION_MINUTES)

    session_id = start_session(engine, group_id=group_id)

    with engine.begin() as conn:
        conn.execute(
            update(class_sessions)
            .where(class_sessions.c.id == session_id)
            .values(started_at=started_at)
        )

    for student in students:
        profile = profile_map[student.id]
        attendance_prob = ATTENDANCE_PROFILES[profile]

        if random.random() > attendance_prob:
            continue  # absent this session

        late_minutes = 0 if random.random() > 0.2 else random.randint(5, 20)
        entry_time = started_at + timedelta(minutes=late_minutes)

        early_leave = 0 if random.random() > 0.15 else random.randint(5, 25)
        exit_time = ended_at - timedelta(minutes=early_leave)

        with engine.begin() as conn:
            conn.execute(
                insert(attendance_events).values(
                    session_id=session_id,
                    student_id=student.id,
                    event_type="entry",
                    timestamp=entry_time,
                )
            )
            conn.execute(
                insert(attendance_events).values(
                    session_id=session_id,
                    student_id=student.id,
                    event_type="exit",
                    timestamp=exit_time,
                )
            )

    end_session(engine, session_id)
    with engine.begin() as conn:
        conn.execute(
            update(class_sessions)
            .where(class_sessions.c.id == session_id)
            .values(ended_at=ended_at)
        )

    print(f"Session simulated: {started_at.strftime('%Y-%m-%d')}")


def main():
    engine = get_engine()
    students = get_students_by_group(engine, GROUP_ID)
    profile_map = assign_profiles(students)

    print("Assigned profiles:")
    for s in students:
        print(f"  {s.full_name}: {profile_map[s.id]}")
    print()

    start_date = datetime.utcnow() - timedelta(days=NUM_SESSIONS * DAYS_BETWEEN_SESSIONS)

    for i in range(NUM_SESSIONS):
        session_date = start_date + timedelta(days=i * DAYS_BETWEEN_SESSIONS)
        simulate_session(engine, GROUP_ID, session_date, students, profile_map)

    print(f"\n{NUM_SESSIONS} sessions simulated successfully.")


if __name__ == "__main__":
    main()
