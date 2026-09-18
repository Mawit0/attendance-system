"""Frame annotation utilities.

Draws bounding boxes on a camera frame to visualize what both ML
models detected: YOLO's person detections (yellow) and InsightFace's
identified faces (green, labeled with the student's name). Currently
used only for debugging — the annotated frame is written to disk by
the worker but is not displayed in the Streamlit UI, since a
continuously updating live video feed was evaluated and intentionally
not built (see project documentation for the reasoning).
"""

import cv2


def annotate_frame(frame, yolo_boxes: list, identified_faces: dict):
    """Draw detection boxes and labels onto a copy of a frame.

    Args:
        frame: The original BGR frame (not modified in place).
        yolo_boxes: List of [x1, y1, x2, y2] boxes from
            ``detect_people_boxes``, drawn in yellow.
        identified_faces: Dict mapping a face's bounding box (as a
            tuple) to (student_id, full_name), drawn in green with the
            student's first name as a label.

    Returns:
        A new frame with all boxes and labels drawn on it.
    """
    annotated = frame.copy()

    for box in yolo_boxes:
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 255), 2)

    for bbox, (student_id, full_name) in identified_faces.items():
        x1, y1, x2, y2 = map(int, bbox)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(annotated, full_name.split()[0], (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    return annotated