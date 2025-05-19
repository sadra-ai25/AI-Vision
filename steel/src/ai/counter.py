from ultralytics import YOLO
import cv2

class IngotCounter:
    def __init__(self, model_path, counting_line_x, rabbitmq_client, queue_name, match_threshold=5):
        self.model = YOLO(model_path)
        self.counting_line_x = counting_line_x
        self.match_threshold = match_threshold
        self.counted_ids = set()
        self.rabbitmq_client = rabbitmq_client
        self.queue_name = queue_name

    def process_frame(self, frame):
        results = self.model.track(frame, persist=True)
        counted_ingots = []
        for box in results[0].boxes:
            if box.id is None:
                continue
            id = int(box.id.item())
            x, y, w, h = box.xywh[0].tolist()
            centroid_x = x
            if abs(centroid_x - self.counting_line_x) <= self.match_threshold and id not in self.counted_ids:
                counted_ingots.append((id, h, w))
                self.counted_ids.add(id)
        count = len(counted_ingots)
        sizes = [size for _, size, _ in counted_ingots]
        widths = [width for _, _, width in counted_ingots]
        return count, sizes, widths, results