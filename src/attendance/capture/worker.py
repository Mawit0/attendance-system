# src/attendance/capture/worker.py

import sys
import time
import cv2
from pathlib import Path

from attendance.recognition.person_detector import count_people
from attendance.config import RECOGNITION_INTERVAL_SECONDS, DATA_DIR
from attendance.db.connection import get_engine
from attendance.db.queries import start_session, end_session
from attendance.recognition.matcher import FaceMatcher
from attendance.tracking.presence import PresenceTracker
from attendance.enrollment.embeddings import get_face_app
from attendance.db.queries import log_snapshot

STOP_SIGNAL_PATH = DATA_DIR / ".stop_signal"
CAMERA_INDEX = 1  # ajustar según qué índice le corresponda a Iriun


def should_stop() -> bool:
    return STOP_SIGNAL_PATH.exists()


def clear_stop_signal() -> None:
    if STOP_SIGNAL_PATH.exists():
        STOP_SIGNAL_PATH.unlink()


def detect_all_faces(frame) -> list:
    """Regresa la lista de embeddings de todas las caras detectadas en el frame."""
    app = get_face_app()
    faces = app.get(frame)
    return [f.embedding for f in faces]


def run_worker(group_id: int) -> None:
    clear_stop_signal()

    engine = get_engine()
    session_id = start_session(engine, group_id=group_id)
    print(f"Sesión iniciada: id={session_id}")

    matcher = FaceMatcher(engine)
    tracker = PresenceTracker(engine, session_id)

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_AVFOUNDATION)
    if not cap.isOpened():
        print("ERROR: no se pudo abrir la cámara.")
        sys.exit(1)

    print(f"Worker corriendo. Revisando cada {RECOGNITION_INTERVAL_SECONDS}s. "
          f"Crea {STOP_SIGNAL_PATH} para detener.")

    try:
        while True:
            if should_stop():
                print("Señal de detención recibida.")
                break

            ret, frame = cap.read()
            if not ret:
                print("ADVERTENCIA: no se pudo leer frame de la cámara.")
                time.sleep(RECOGNITION_INTERVAL_SECONDS)
                continue

            people_count = count_people(frame) 

            live_embeddings = detect_all_faces(frame)
            detected_ids = set()

            for embedding in live_embeddings:
                student_id, score = matcher.identify(embedding)
                if student_id is not None:
                    detected_ids.add(student_id)

            tracker.process_detected_students(detected_ids)
            log_snapshot(engine, session_id, people_detected=people_count, people_identified=len(detected_ids))
            print(f"[{time.strftime('%H:%M:%S')}] Detectados: {detected_ids or 'ninguno'}")

            time.sleep(RECOGNITION_INTERVAL_SECONDS)

    finally:
        print("Finalizando sesión...")
        tracker.finalize_session()
        end_session(engine, session_id)
        cap.release()
        clear_stop_signal()
        print("Worker detenido limpiamente.")
        print(f"[{time.strftime('%H:%M:%S')}] Detectados: {detected_ids or 'ninguno'} | Personas visibles: {people_count}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--group-id", type=int, required=True)
    args = parser.parse_args()
    run_worker(group_id=args.group_id)
