# scripts/seed_base_data.py
"""
Carga los datos base conocidos: teacher, subject, groups.
Correr una sola vez (o verificar antes de re-correr, para no duplicar filas).
"""
from attendance.db.connection import get_engine
from attendance.db.queries import create_teacher, create_subject, create_group

def main():
    engine = get_engine()

    teacher_id = create_teacher(engine, full_name="Mauricio Gabriel Ramírez Rubio")
    print(f"Teacher creado: id={teacher_id}")

    subject_id = create_subject(engine, name="Visual Modeling for Information", teacher_id=teacher_id)
    print(f"Subject creado: id={subject_id}")

    group_9a_id = create_group(engine, name="9A", subject_id=subject_id)
    group_9b_id = create_group(engine, name="9B", subject_id=subject_id)
    print(f"Groups creados: 9A={group_9a_id}, 9B={group_9b_id}")

if __name__ == "__main__":
    main()
