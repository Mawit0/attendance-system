# scripts/poc_face_recognition.py
import cv2
import numpy as np
from insightface.app import FaceAnalysis

app = FaceAnalysis(name="buffalo_l", providers=["CoreMLExecutionProvider", "CPUExecutionProvider"])
app.prepare(ctx_id=0)

def get_embedding(path):
    img = cv2.imread(path)
    faces = app.get(img)
    if not faces:
        print(f"No se detectó cara en: {path}")
        return None
    return faces[0].embedding

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Dos fotos TUYAS distintas
emb1 = get_embedding("data/student_photos/MAURICIO_GABRIEL_RAMIREZ_RUBIO_2309192/foto1.jpg")
emb2 = get_embedding("data/student_photos/MAURICIO_GABRIEL_RAMIREZ_RUBIO_2309192/foto2.jpg")

# Una foto de otro estudiante
emb3 = get_embedding("data/student_photos/DALILA_DE_LOS_ANGELES_KU_DZUL_2309132/foto1.jpeg")

if emb1 is not None and emb2 is not None:
    print(f"Similitud (mismo estudiante): {cosine_similarity(emb1, emb2):.4f}")

if emb1 is not None and emb3 is not None:
    print(f"Similitud (estudiantes distintos): {cosine_similarity(emb1, emb3):.4f}")
