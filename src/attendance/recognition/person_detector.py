# src/attendance/recognition/person_detector.py

from ultralytics import YOLO

_model = None

def get_person_detector():
    """Singleton — evita recargar el modelo en cada llamada."""
    global _model
    if _model is None:
        _model = YOLO("yolo11n.pt")
    return _model


def count_people(frame) -> int:
    """
    Regresa el número de personas detectadas en el frame.
    Clase 0 en COCO = 'person'.
    """
    model = get_person_detector()
    results = model(frame, classes=[0], verbose=False)
    return len(results[0].boxes)
