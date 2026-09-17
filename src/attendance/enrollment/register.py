# src/attendance/enrollment/register.py

import re
from pathlib import Path
from attendance.enrollment.embeddings import generate_embedding
from attendance.db.queries import create_student, add_face_embedding

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def parse_folder_name(folder_name: str) -> tuple[str, str]:
    """
    'MAURICIO_GABRIEL_RAMIREZ_RUBIO_2309192' -> ('Mauricio Gabriel Ramirez Rubio', '2309192')
    Asume que el último segmento separado por '_' es la matrícula (todo dígitos).
    """
    parts = folder_name.split("_")
    if not parts[-1].isdigit():
        raise ValueError(f"No se pudo extraer matrícula de: {folder_name}")

    student_id = parts[-1]
    full_name = " ".join(parts[:-1]).title()
    return full_name, student_id


def enroll_student_folder(engine, folder: Path, group_id: int) -> None:
    full_name, student_id = parse_folder_name(folder.name)
    print(f"Procesando: {full_name} ({student_id})")

    create_student(engine, student_id=student_id, full_name=full_name, group_id=group_id)

    photo_files = [f for f in folder.iterdir() if f.suffix.lower() in VALID_EXTENSIONS]
    if not photo_files:
        print(f"  ⚠ Sin fotos válidas en {folder.name}")
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

    print(f"  ✓ {success_count}/{len(photo_files)} embeddings generados")


def enroll_all_students(engine, photos_root: Path, group_id: int) -> None:
    student_folders = [f for f in photos_root.iterdir() if f.is_dir()]
    print(f"Encontradas {len(student_folders)} carpetas de estudiantes\n")

    for folder in sorted(student_folders):
        enroll_student_folder(engine, folder, group_id)
        print()
