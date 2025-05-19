import logging
import pickle
import time
import cv2
import numpy as np
import datetime
from datetime import datetime
from zoneinfo import ZoneInfo  

import os
import csv
from rabbitmq.client import RabbitMQClient
from ai.barcode import process_frame_for_barcode
from ai.counter import IngotCounter
from db.database import DatabaseLogger
from config.config import settings
# Dictionary to track the last saved barcode for each source
last_saved_barcodes = {}

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

def save_image_to_folder(cropped_image, barcode):
    os.makedirs(settings.CROPPED_IMAGES_PATH, exist_ok=True)
    cv2.putText(cropped_image, barcode, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
    image_filename = os.path.join(settings.CROPPED_IMAGES_PATH, f"{barcode}.jpg")
    cv2.imwrite(image_filename, cropped_image)
    logger.info(f"Saved cropped image with barcode {barcode} to {image_filename}")

def frame_consumer(source_id, source_path=None, source_type='camera', stop_event=None):
    # select source config
    if source_type == 'camera':
        source_info = settings.CAMERAS.get(source_id)
    elif source_type == 'video':
        source_info = settings.VIDEOS.get(source_id)
    if not source_info:
        logger.error(f"Source {source_id} not found in configuration")
        return
    
    bbox = source_info.get('bbox', settings.DEFAULT_BBOX)
    counting_line_x = source_info.get('counting_line_x', settings.DEFAULT_COUNTING_LINE_X)

    # setup clients
    rabbitmq_client = RabbitMQClient(
        settings.RABBITMQ_HOST, settings.RABBITMQ_PORT,
        settings.RABBITMQ_USER, settings.RABBITMQ_PASS
    )
    rabbitmq_client.connect()

    counter = IngotCounter(
        model_path='src/ai/weights/best.pt',
        counting_line_x=counting_line_x,
        rabbitmq_client=rabbitmq_client,
        queue_name=f"frame_queue_{source_id}",
        match_threshold=5
    )
    db_logger = DatabaseLogger()
    output_dir = os.path.join(settings.FRAMES_PATH, source_id)
    os.makedirs(output_dir, exist_ok=True)

    frame_count = 0
    ingot_count = 0
    target_time = 1.0 / settings.FRAME_RATE

    try:
        while stop_event is None or not stop_event.is_set():
            t_start = time.time()

            msg = rabbitmq_client.basic_get(f"frame_queue_{source_id}")
            if msg is None:
                logger.info(f"{source_id} - No frames available, Waiting...")
                time.sleep(0.05)
                continue

            data = pickle.loads(msg)
            frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                logger.warning(f"{source_id} - corrupted frame detected, Skipping...")
                continue

            # barcode
            barcode, croped = process_frame_for_barcode(frame, bbox)
            if barcode and last_saved_barcodes.get(source_id) != barcode:
                dt = datetime.fromtimestamp(timestamp, tz=ZoneInfo("Asia/Tehran"))
                frame_datetime = dt.strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"Detected new barcode: {barcode} from {source_type} in {source_id}")
                save_image_to_folder(croped, barcode)
                db_logger.log_barcode(source_id, barcode, frame_datetime, data, "")
                last_saved_barcodes[source_id] = barcode
            else:
                logger.debug(f"Duplicate barcode {barcode} detected, skipping save.")

            # ingot counting
            count, sizes, widths, results = counter.process_frame(frame)
            ingot_count += count
            # annotate if needed
            for box in (results[0].boxes if results and results[0].boxes else []):
                x, y, w, h = box.xywh[0].tolist()
                x1, y1 = int(x - w / 2), int(y - h / 2)
                x2, y2 = int(x + w / 2), int(y + h / 2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.line(frame, (counting_line_x, 0), (counting_line_x, frame.shape[0]), (0, 255, 0), 2)
            cv2.putText(frame, f"ingot_count: {ingot_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

            frame_count += 1
            # save only if event
            if count > 0:
                frame_path = os.path.join(output_dir, f"frame_{frame_count:04d}.jpg")
                cv2.imwrite(frame_path, frame)
                logger.info(f"{source_id} saved frame {frame_count}, ingot_count = {ingot_count}")
                dt = datetime.fromtimestamp(timestamp, tz=ZoneInfo("Asia/Tehran"))
                frame_datetime = dt.strftime('%Y-%m-%d %H:%M:%S')
                # db log ingot
                try:
                    db_logger.log_ingot(source_id, sizes[0] if sizes else 0, widths[0] if widths else 0, frame_datetime, frame, "")
                except Exception as db_error:
                    logger.error(f"{source_id} - Database error: {db_error}")
                    time.sleep(0.1)
                    continue          
            # throttle
            elapsed = time.time() - t_start
            if elapsed < target_time:
                time.sleep(target_time - elapsed)

    except Exception as e:
        logger.error(f"Consumer {source_id} intrupped, shutting down and error: {e}")
    finally:
        try:
            db_logger.close()
            rabbitmq_client.close()
        except Exception as e:
            logger.error(f"Error in frame consumer for {source_type} {source_id}: {e}")
