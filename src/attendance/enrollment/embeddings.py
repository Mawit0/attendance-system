"""Face embedding generation using InsightFace.

Provides a singleton-loaded InsightFace model (to avoid reloading it
on every call) and a helper to generate a face embedding from a single
image file, used during the enrollment pipeline.
"""

from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis

_app = None


def get_face_app() -> FaceAnalysis:
    """Return a shared InsightFace FaceAnalysis instance, loading it on
    first use.

    Uses the CoreML execution provider when available (to take
    advantage of Apple Silicon's Neural Engine), falling back to CPU
    otherwise.

    Returns:
        A prepared FaceAnalysis instance, ready for inference.
    """
    global _app
    if _app is None:
        _app = FaceAnalysis(
            name="buffalo_l",
            providers=["CoreMLExecutionProvider", "CPUExecutionProvider"],
        )
        _app.prepare(ctx_id=0)
    return _app


def generate_embedding(image_path: Path) -> np.ndarray | None:
    """Generate a face embedding from a single image file.

    If multiple faces are detected in the image, the largest one (by
    bounding box area) is used, on the assumption that it is the
    intended subject rather than someone in the background.

    Args:
        image_path: Path to the image file.

    Returns:
        A 512-dimensional float32 embedding, or None if the image
        could not be read or no face was detected in it.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"  Could not read image: {image_path.name}")
        return None

    faces = get_face_app().get(img)
    if not faces:
        print(f"  No face detected in: {image_path.name}")
        return None

    if len(faces) > 1:
        print(f"  Multiple faces detected in {image_path.name}, using the largest one")

    faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
    return faces[0].embedding