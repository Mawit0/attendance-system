"""Camera worker process.

Runs as an independent subprocess (launched by Streamlit) to keep
camera capture and ML inference off the main Streamlit thread — since
Streamlit re-runs its script on every UI interaction, running face
recognition inline would freeze the interface. This worker owns the
camera connection, runs the recognition cycle, and writes all results
directly to the database; the Streamlit UI only ever reads.
"""

import sys
import time
from pathlib import Path

import cv2

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

# Camera index for Iriun Webcam, confirmed empirically on the
# development machine (index 0 was the built-in laptop camera).
# Adjust if running on a different setup.
CAMERA_INDEX = 1


def should_stop() -> bool:
    """Check whether the Streamlit UI has requested this worker to stop.

    Uses a flag file rather than OS signals, since it is simpler to
    reason about, easy to trigger manually for debugging, and portable
    across operating systems.
    """
    return STOP_SIGNAL_PATH.exists()


def clear_stop_signal() -> None:
    """Remove the stop flag file, if present."""
    if STOP_SIGNAL_PATH.exists():
        STOP_SIGNAL_PATH.unlink()


def detect_all_faces(frame) -> list:
    """Detect every face in a frame and return their embeddings and boxes.

    Returns:
        A list of (embedding, bbox) tuples, one per detected face.
    """
    app = get_face_app()
    faces = app.get(frame)
    return [(f.embedding, f.bbox) for f in faces]


def run_worker(group_id: int) -> None:
    """Run the camera worker loop for a class session.

    Starts a new session, then repeatedly: captures a frame, runs
    person detection (YOLO) and face recognition (InsightFace), feeds
    the results into the presence tracker, logs a detection snapshot,
    and sleeps until the next cycle. Stops when a stop signal is
    detected or the process is interrupted, always finalizing the
    session cleanly via the ``finally`` block.

    Args:
        group_id: ID of the group this class session belongs to.
    """
    clear_stop_signal()

    engine = get_engine()
    session_id = start_session(engine, group_id=group_id)
    print(f"Session started: id={session_id}")

    matcher = FaceMatcher(engine)
    tracker = PresenceTracker(engine, session_id)

    students = get_students_by_group(engine, group_id)
    student_names = {s.id: s.full_name for s in students}

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_AVFOUNDATION)
    if not cap.isOpened():
        print("ERROR: could not open the camera.")
        sys.exit(1)

    print(f"Worker running. Checking every {RECOGNITION_INTERVAL_SECONDS}s. "
          f"Create {STOP_SIGNAL_PATH} to stop.")

    try:
        while True:
            if should_stop():
                print("Stop signal received.")
                break

            ret, frame = cap.read()
            if not ret:
                print("WARNING: could not read a frame from the camera.")
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

            print(f"[{time.strftime('%H:%M:%S')}] Detected: {detected_ids or 'none'} "
                  f"| People visible: {len(people_boxes)}")

            time.sleep(RECOGNITION_INTERVAL_SECONDS)

    finally:
        print("Finalizing session...")
        tracker.finalize_session()
        end_session(engine, session_id)
        cap.release()
        clear_stop_signal()
        if LATEST_FRAME_PATH.exists():
            LATEST_FRAME_PATH.unlink()
        print("Worker stopped cleanly.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--group-id", type=int, required=True)
    args = parser.parse_args()
    run_worker(group_id=args.group_id)