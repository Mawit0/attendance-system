# src/attendance/enrollment/embeddings.py

import cv2
import numpy as np
from pathlib import Path
from insightface.app import FaceAnalysis

_app = None

def get_face_app():
    """Singleton — evita recargar el modelo en cada llamada."""
    global _app
    if _app is None:
        _app = FaceAnalysis(
            name="buffalo_l",
            providers=["CoreMLExecutionProvider", "CPUExecutionProvider"],
        )
        _app.prepare(ctx_id=0)
    return _app


def generate_embedding(image_path: Path) -> np.ndarray | None:
    """Regresa el embedding de la primera cara detectada, o None si falla."""
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"  ⚠ No se pudo leer: {image_path.name}")
        return None

    faces = get_face_app().get(img)
    if not faces:
        print(f"  ⚠ No se detectó cara en: {image_path.name}")
        return None

    if len(faces) > 1:
        print(f"  ⚠ Múltiples caras detectadas en {image_path.name}, usando la más grande")

    # Si hay varias caras, tomamos la de mayor área (bbox más grande) — asumimos que es el sujeto principal
    faces.sort(key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]), reverse=True)
    return faces[0].embedding
