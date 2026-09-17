# scripts/test_matcher.py
from attendance.db.connection import get_engine
from attendance.recognition.matcher import FaceMatcher
from attendance.enrollment.embeddings import generate_embedding
from pathlib import Path

engine = get_engine()
matcher = FaceMatcher(engine)

# Prueba con una foto conocida
test_photo = Path("data/student_photos/MAURICIO_GABRIEL_RAMIREZ_RUBIO_2309192/foto5.jpg")
embedding = generate_embedding(test_photo)

student_id, score = matcher.identify(embedding)
print(f"Identificado: {student_id} (score={score:.4f})")
