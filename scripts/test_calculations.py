# scripts/test_calculations.py
from attendance.db.connection import get_engine
from attendance.reports.calculations import calculate_attendance_percentage

engine = get_engine()

SESSION_ID = 1
STUDENT_ID = "2309192"

pct = calculate_attendance_percentage(engine, SESSION_ID, STUDENT_ID)
print(f"Asistencia de {STUDENT_ID} en sesión {SESSION_ID}: {pct:.1f}%")
