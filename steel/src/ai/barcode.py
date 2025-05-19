from paddleocr import PaddleOCR
import numpy as np
import cv2
import re
import os
os.environ["CPU_DISABLE_ONE_DNN"] = "1"

ocr = PaddleOCR(
    lang='en',
    det_model_dir='src/ai/weights/en_PP-OCRv3_det_infer',
    rec_model_dir='src/ai/weights/en_PP-OCRv4_rec_infer',
    cls_model_dir='src/ai/weights/ch_ppocr_mobile_v2.0_cls_infer',
    use_angle_cls=True,
    det_db_thresh=0.3,
    rec_batch_num=6,
    use_gpu=False,
    enable_mkldnn=False
)

def process_frame_for_barcode(frame: np.ndarray, bbox: dict):
    cropped_img = frame[bbox["y_min"]:bbox["y_max"], bbox["x_min"]:bbox["x_max"]]
    try:
        # frame = cv2.resize(frame, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        if cropped_img.size == 0:
            return None, None
        results = ocr.ocr(cropped_img, cls=True)
        if not results or not isinstance(results, list) or len(results) == 0:
            return None, None
        detected_texts = [line[1][0] for block in results for line in block if line and len(line) >= 2]
        if not detected_texts:
            return None, None
        full_text = ' '.join(detected_texts)
        numbers = re.findall(r'\d+', full_text)
        for number in numbers:
            if len(number) == 8:
                return number, cropped_img
        return None, None
    except Exception as e:
        print(f"Error processing frame for barcode: {e}")
        return None, None