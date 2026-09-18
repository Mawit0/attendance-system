# src/attendance/recognition/annotate.py

import cv2


def annotate_frame(frame, yolo_boxes, identified_faces: dict):
    """
    yolo_boxes: lista de cajas [x1, y1, x2, y2] de personas detectadas por YOLO
    identified_faces: dict {bbox_tuple: (student_id, full_name)} de InsightFace
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


