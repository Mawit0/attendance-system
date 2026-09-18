"""Face matching against enrolled students.

Compares a live face embedding (captured during a class session)
against every stored embedding for every enrolled student, using
cosine similarity. Returns the best match if its similarity score
clears the configured threshold, otherwise reports no match.
"""

import numpy as np

from attendance.db.queries import get_all_embeddings
from attendance.config import MATCH_THRESHOLD


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute the cosine similarity between two embedding vectors.

    Returns:
        A value between -1 and 1, where 1 means identical direction
        (same identity) and values near 0 or negative indicate
        unrelated faces.
    """
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def bytes_to_embedding(embedding_bytes: bytes) -> np.ndarray:
    """Deserialize a stored embedding back into a numpy array.

    Must use float32, matching the dtype InsightFace produces and the
    one used when the embedding was originally serialized with
    ``.tobytes()`` during enrollment. Using a different dtype here
    would silently corrupt the values without raising an error.
    """
    return np.frombuffer(embedding_bytes, dtype=np.float32)


class FaceMatcher:
    """Matches live face embeddings against enrolled students.

    Loads all known embeddings into memory once at construction time,
    avoiding a database round-trip on every frame processed by the
    camera worker. At the current scale (hundreds of embeddings), a
    linear scan per match is fast enough that no indexing structure
    (e.g. FAISS) is needed.
    """

    def __init__(self, engine):
        self._engine = engine
        self._known_embeddings: list[tuple[str, np.ndarray]] = []
        self.reload(engine)

    def reload(self, engine) -> None:
        """Re-fetch all known embeddings from the database.

        Useful if students are enrolled after the matcher was first
        created, without needing to restart the worker process.
        """
        rows = get_all_embeddings(engine)
        self._known_embeddings = [
            (row.student_id, bytes_to_embedding(row.embedding))
            for row in rows
        ]
        print(f"Matcher loaded with {len(self._known_embeddings)} known embeddings")

    def identify(self, live_embedding: np.ndarray) -> tuple[str | None, float]:
        """Identify the best-matching student for a live embedding.

        Compares against every stored embedding for every student and
        keeps the single highest-scoring match (best-match strategy),
        which favors recall over strict averaging — appropriate here
        because the primary defense against misidentifying students is
        the similarity threshold itself, not the aggregation method.

        Args:
            live_embedding: The embedding to identify, from a face
                detected in a live camera frame.

        Returns:
            A tuple of (student_id, similarity_score). If no known
            embedding clears the match threshold, student_id is None
            and similarity_score is the best score found anyway (for
            debugging/logging purposes).
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