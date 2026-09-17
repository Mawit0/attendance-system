# src/attendance/recognition/matcher.py

import numpy as np
from attendance.db.queries import get_all_embeddings
from attendance.config import MATCH_THRESHOLD


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def bytes_to_embedding(embedding_bytes: bytes) -> np.ndarray:
    """Debe usar el mismo dtype con el que se guardó en enrollment."""
    return np.frombuffer(embedding_bytes, dtype=np.float32)


class FaceMatcher:
    """
    Carga todos los embeddings conocidos en memoria una sola vez
    (evita golpear la DB en cada frame procesado).
    """

    def __init__(self, engine):
        self._engine = engine
        self._known_embeddings: list[tuple[str, np.ndarray]] = []
        self.reload(engine)

    def reload(self, engine) -> None:
        rows = get_all_embeddings(engine)
        self._known_embeddings = [
            (row.student_id, bytes_to_embedding(row.embedding))
            for row in rows
        ]
        print(f"Matcher cargado con {len(self._known_embeddings)} embeddings conocidos")

    def identify(self, live_embedding: np.ndarray) -> tuple[str | None, float]:
        """
        Regresa (student_id, similarity) del mejor match, o (None, best_score)
        si nadie supera el threshold.
        """
        if not self._known_embeddings:
            return None, 0.0

        best_student_id = None
        best_score = -1.0

        for student_id, known_embedding in self._known_embeddings:
            score = cosine_similarity(live_embedding, known_embedding)
            if score > best_score:
                best_score = score
                best_student_id = student_id

        if best_score >= MATCH_THRESHOLD:
            return best_student_id, best_score

        return None, best_score
