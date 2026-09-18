# src/attendance/capture/worker.py

import sys
import time
import cv2
from pathlib import Path

from attendance.config import RECOGNITION_INTERVAL_SECONDS, DATA_DIR
from attendance.db.connection import get_engine
from attendance.db.queries import start_session, end_session, log_snapshot, get_students_by_group
from attendance.recognition.matcher import FaceMatcher
from attendance.recognition.person_detector import detect_people_boxes
from attendance.recognition.annotate import annotate_frame
from attendance.tracking.presence import PresenceTracker
from attendance.enrollment.embeddings import get_face_app

STOP_SIGNAL_PATH = DATA_DIR / ".stop_signal"
LATEST_FRAME_PATH = DATA_DIR / "latest_frame.jpg"
CAMERA_INDEX = 1  # Iriun, confirmado empíricamente


def should_stop() -> bool:
    return STOP_SIGNAL_PATH.exists()


def clear_stop_signal() -> None:
    if STOP_SIGNAL_PATH.exists():
        STOP_SIGNAL_PATH.unlink()


def detect_all_faces(frame) -> list:
    """Regresa lista de (embedding, bbox) para cada cara detectada en el frame."""
    app = get_face_app()
    faces = app.get(frame)
    return [(f.embedding, f.bbox) for f in faces]


def run_worker(group_id: int) -> None:
    clear_stop_signal()

    engine = get_engine()
    session_id = start_session(engine, group_id=group_id)
    print(f"Sesión iniciada: id={session_id}")

    matcher = FaceMatcher(engine)
    tracker = PresenceTracker(engine, session_id)

    students = get_students_by_group(engine, group_id)
    student_names = {s.id: s.full_name for s in students}

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

            people_boxes = detect_people_boxes(frame)
            faces_with_boxes = detect_all_faces(frame)

            detected_ids = set()
            identified_faces = {}  # {bbox_tuple: (student_id, full_name)}

            for embedding, bbox in faces_with_boxes:
                student_id, score = matcher.identify(embedding)
                if student_id is not None:
                    detected_ids.add(student_id)
                    full_name = student_names.get(student_id, student_id)
                    identified_faces[tuple(bbox)] = (student_id, full_name)

            annotated = annotate_frame(frame, people_boxes, identified_faces)
            cv2.imwrite(str(LATEST_FRAME_PATH), annotated)

            tracker.process_detected_students(detected_ids)
            log_snapshot(engine, session_id, people_detected=len(people_boxes), people_identified=len(detected_ids))

            print(f"[{time.strftime('%H:%M:%S')}] Detectados: {detected_ids or 'ninguno'} "
                  f"| Personas visibles: {len(people_boxes)}")

            time.sleep(RECOGNITION_INTERVAL_SECONDS)

    finally:
        print("Finalizando sesión...")
        tracker.finalize_session()
        end_session(engine, session_id)
        cap.release()
        clear_stop_signal()
        if LATEST_FRAME_PATH.exists():
            LATEST_FRAME_PATH.unlink()
        print("Worker detenido limpiamente.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--group-id", type=int, required=True)
    args = parser.parse_args()
    run_worker(group_id=args.group_id)