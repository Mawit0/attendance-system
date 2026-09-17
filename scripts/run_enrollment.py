# scripts/run_enrollment.py
from pathlib import Path
from attendance.db.connection import get_engine
from attendance.enrollment.register import enroll_all_students

GROUP_9A_ID = 1  # el id que te devolvió el seed

def main():
    engine = get_engine()
    photos_root = Path("data/student_photos")
    enroll_all_students(engine, photos_root, group_id=GROUP_9A_ID)
    print("Enrollment completo.")

if __name__ == "__main__":
    main()
