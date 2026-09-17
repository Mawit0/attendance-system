# scripts/test_tracking.py
from attendance.db.connection import get_engine
from attendance.db.queries import start_session
from attendance.tracking.presence import PresenceTracker

engine = get_engine()
session_id = start_session(engine, group_id=1)
print(f"Sesión de prueba creada: id={session_id}\n")

tracker = PresenceTracker(engine, session_id)

# Ciclo 1: Mauricio y Dalila presentes
print("Ciclo 1: {2309192, 2309132}")
tracker.process_detected_students({"2309192", "2309132"})

# Ciclo 2: Mauricio sigue, Dalila ya no se detecta
print("Ciclo 2: {2309192}")
tracker.process_detected_students({"2309192"})

# Ciclo 3: Dalila sigue sin detectarse
print("Ciclo 3: {2309192}")
tracker.process_detected_students({"2309192"})

# Ciclo 4: Dalila sigue sin detectarse -> debería disparar 'exit' (3 misses)
print("Ciclo 4: {2309192}")
tracker.process_detected_students({"2309192"})

# Ciclo 5: Dalila vuelve -> debería disparar nuevo 'entry'
print("Ciclo 5: {2309192, 2309132}")
tracker.process_detected_students({"2309192", "2309132"})

# Fin de la clase
print("\nFinalizando sesión...")
tracker.finalize_session()

# Revisar qué quedó guardado
from attendance.db.queries import get_events_for_session
events = get_events_for_session(engine, session_id)
print(f"\nEventos registrados ({len(events)}):")
for e in events:
    print(f"  {e.student_id} - {e.event_type} - {e.timestamp}")
