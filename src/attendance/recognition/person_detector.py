from ultralytics import YOLO
_model = None

def get_person_detector():
    global _model
    if _model is None:
        _model = YOLO("yolo11n.pt")
    return _model

def detect_people_boxes(frame, confidence_threshold=0.5):
    model = get_person_detector()
    results = model(frame, classes=[0], conf=confidence_threshold, verbose=False)
    return [box.xyxy[0].tolist() for box in results[0].boxes]