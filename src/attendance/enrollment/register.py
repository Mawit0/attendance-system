"""Student enrollment pipeline.

Provides two enrollment paths:

1. Batch enrollment from a folder structure (used for the initial
   dataset load via ``scripts/run_enrollment.py``), where each
   student's photos live in a folder named after them.
2. Single-student enrollment from uploaded files (used by the
   Streamlit "Add new student" form), which accepts photos already
   held in memory rather than a folder on disk.

Both paths ultimately generate one face embedding per valid photo and
store them via the database layer.
"""

from pathlib import Path

import cv2
import numpy as np

from attendance.enrollment.embeddings import generate_embedding, get_face_app
from attendance.db.queries import create_student, add_face_embedding, get_student_by_id

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def parse_folder_name(folder_name: str) -> tuple[str, str]:
    """Extract a student's full name and ID from a folder name.

    Expects the format ``FIRST_MIDDLE_LAST_STUDENTID``, where the last
    underscore-separated segment is a numeric student ID. For example,
    ``"MAURICIO_GABRIEL_RAMIREZ_RUBIO_2309192"`` becomes
    ``("Mauricio Gabriel Ramirez Rubio", "2309192")``.

    Args:
        folder_name: The folder's name, following the expected format.

    Returns:
        A tuple of (full_name, student_id).

    Raises:
        ValueError: If the last segment is not numeric, so a malformed
            folder name fails loudly instead of silently producing a
            wrong student ID.
    """
    parts = folder_name.split("_")
    if not parts[-1].isdigit():
        raise ValueError(f"Could not extract a student ID from: {folder_name}")

    student_id = parts[-1]
    full_name = " ".join(parts[:-1]).title()
    return full_name, student_id


def enroll_student_folder(engine, folder: Path, group_id: int) -> None:
    """Enroll a single student from a folder of photos.

    Creates the student record, then generates and stores one
    embedding per valid photo found in the folder.

    Args:
        engine: SQLAlchemy engine.
        folder: Path to the student's photo folder, named per
            ``parse_folder_name``'s expected format.
        group_id: ID of the group the student belongs to.
    """
    full_name, student_id = parse_folder_name(folder.name)
    print(f"Processing: {full_name} ({student_id})")

    create_student(engine, student_id=student_id, full_name=full_name, group_id=group_id)

    photo_files = [f for f in folder.iterdir() if f.suffix.lower() in VALID_EXTENSIONS]
    if not photo_files:
        print(f"  No valid photos in {folder.name}")
        return

    success_count = 0
    for photo in sorted(photo_files):
        embedding = generate_embedding(photo)
        if embedding is not None:
            add_face_embedding(
                engine,
                student_id=student_id,
                embedding_bytes=embedding.tobytes(),
                source_photo=photo.name,
            )
            success_count += 1

    print(f"  {success_count}/{len(photo_files)} embeddings generated")


def enroll_all_students(engine, photos_root: Path, group_id: int) -> None:
    """Enroll every student found under a root photos directory.

    Iterates over each subfolder (one per student) and enrolls them
    via ``enroll_student_folder``.

    Args:
        engine: SQLAlchemy engine.
        photos_root: Directory containing one subfolder per student.
        group_id: ID of the group all these students belong to.
    """
    student_folders = [f for f in photos_root.iterdir() if f.is_dir()]
    print(f"Found {len(student_folders)} student folders\n")

    for folder in sorted(student_folders):
        enroll_student_folder(engine, folder, group_id)
        print()


def enroll_student_from_uploads(engine, student_id: str, full_name: str, group_id: int, uploaded_files: list) -> int:
    """Enroll a single student from files uploaded through the UI.

    Unlike ``enroll_student_folder``, this does not rely on a folder
    naming convention: the student's name and ID are provided
    explicitly, and photos arrive as in-memory file-like objects (from
    Streamlit's file uploader or camera input).

    Args:
        engine: SQLAlchemy engine.
        student_id: The student's ID (matrícula), used as primary key.
        full_name: The student's full name.
        group_id: ID of the group the student belongs to.
        uploaded_files: A list of file-like objects with ``.read()``
            and ``.name``, as returned by Streamlit's upload widgets.

    Returns:
        The number of embeddings successfully generated.

    Raises:
        ValueError: If a student with this ID is already registered,
            to avoid silently overwriting an existing student.
    """
    existing = get_student_by_id(engine, student_id)
    if existing is not None:
        raise ValueError(f"A student with ID {student_id} already exists")

    create_student(engine, student_id=student_id, full_name=full_name, group_id=group_id)

    app = get_face_app()
    success_count = 0

    for uploaded_file in uploaded_files:
        file_bytes = np.frombuffer(uploaded_file.read(), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            continue

        faces = app.get(img)
        if not faces:
            continue

        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        embedding = faces[0].embedding

        add_face_embedding(
            engine,
            student_id=student_id,
            embedding_bytes=embedding.tobytes(),
            source_photo=uploaded_file.name,
        )
        success_count += 1

    return success_count