"""Person detection using YOLO.

Runs a pretrained YOLO model (trained on COCO, which includes a
"person" class) to count and locate people in a camera frame. This is
independent of face recognition: YOLO has no notion of identity, it
only detects that a person is present. It serves as a complementary
signal to InsightFace, surfacing cases where someone is physically in
the room but not identifiable from their current pose or angle.
"""

from ultralytics import YOLO

_model = None


def get_person_detector() -> YOLO:
    """Return a shared YOLO model instance, loading it on first use.

    Uses the nano variant (yolo11n), the smallest and fastest in the
    YOLO family, since this system only needs to detect a small number
    of people per frame on consumer hardware rather than handle
    high-throughput or high-precision detection.

    Returns:
        A loaded YOLO model instance.
    """
    global _model
    if _model is None:
        _model = YOLO("yolo11n.pt")
    return _model


def detect_people_boxes(frame, confidence_threshold: float = 0.5) -> list:
    """Detect people in a frame and return their bounding boxes.

    Args:
        frame: A BGR image (as read by OpenCV).
        confidence_threshold: Minimum detection confidence to count as
            a person. Raised from the YOLO default (~0.25) to 0.5
            after testing showed the lower default produced false
            positives on cluttered backgrounds (e.g. detecting a
            shelf of folded clothes as an extra person).

    Returns:
        A list of [x1, y1, x2, y2] bounding boxes, one per detected
        person.
    """
    model = get_person_detector()
    results = model(frame, classes=[0], conf=confidence_threshold, verbose=False)
    return [box.xyxy[0].tolist() for box in results[0].boxes]