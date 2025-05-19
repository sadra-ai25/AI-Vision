import subprocess
import pickle
import logging
import numpy as np
import cv2
import time
from rabbitmq.client import RabbitMQClient
from config.config import settings

logger = logging.getLogger(__name__)

def camera_producer(camera_id, stop_event=None):
    camera_info = settings.CAMERAS.get(camera_id)
    if not camera_info:
        logger.error(f"Camera {camera_id} not found in configuration")
        return
    rtsp_url = camera_info["rtsp"]
    logger.info(f"Starting camera producer for {camera_id} with URL: {rtsp_url}")
    ffmpeg_cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        "-skip_frame", "nokey",
        '-i', rtsp_url,
        '-r', str(settings.FRAME_RATE),
        "-vsync", "0",
        # '-buffer_size', '1024000',
        '-f', 'image2pipe',
        '-pix_fmt', 'bgr24',
        '-vcodec', 'rawvideo',
        '-'
    ]
    frame_width = 3840
    frame_height = 2160
    frame_size = frame_width * frame_height * 3
    interval = 1.0 / settings.FRAME_RATE
    while stop_event is None or not stop_event.is_set():
        try:
            # process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            rabbitmq_client = RabbitMQClient(
                settings.RABBITMQ_HOST, settings.RABBITMQ_PORT,
                settings.RABBITMQ_USER, settings.RABBITMQ_PASS
            )
            rabbitmq_client.connect()
            buffer = bytearray()
            while process.poll() is None and (stop_event is None or not stop_event.is_set()):
                data = process.stdout.read(frame_size)
                if not data:
                    break
                
                buffer.extend(data)
                while len(buffer) >= frame_size:
                    raw_frame = buffer[:frame_size]
                    buffer = buffer[frame_size:]
                    frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((frame_height, frame_width, 3))
                    _, buffer_img = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    compressed_frame = buffer_img.tobytes()
                    timestamp = time.time()
                    frame_data = {'frame': compressed_frame, 'timestamp': timestamp}
                    t0=time.time()
                    rabbitmq_client.publish(f"frame_queue_{camera_id}", pickle.dumps(frame_data))
                    dt=time.time()-t0
                    logger.info(f"{camera_id} publish {dt:.4f}s")
                    sleep = interval-dt
                    if sleep > 0:
                        time.sleep(sleep)
            process.terminate()
            rabbitmq_client.close()
        except Exception as e:
            logger.error(f"Error in camera producer for {camera_id}: {e}")
            time.sleep(5)
    logger.info(f"Stopping camera producer for {camera_id}")




### video only
def video_producer(video_path, processor_id, stop_event=None):
    cap = cv2.VideoCapture(video_path)
    rabbitmq_client = RabbitMQClient(
        settings.RABBITMQ_HOST, settings.RABBITMQ_PORT,
        settings.RABBITMQ_USER, settings.RABBITMQ_PASS
    )
    rabbitmq_client.connect()
    frame_count = 0
    try:
        while cap.isOpened() and (stop_event is None or not stop_event.is_set()):
            ret, frame = cap.read()
            if not ret:
                break
            try:
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                compressed_frame = buffer.tobytes()
                timestamp = time.time()
                frame_data = {'frame': compressed_frame, 'timestamp': timestamp}
                rabbitmq_client.publish(f"frame_queue_{processor_id}", pickle.dumps(frame_data))
                frame_count += 1
                logger.info(f"Video {processor_id} - Frame {frame_count} sent to RabbitMQ")
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error in video producer for {processor_id}: {e}")
    finally:
        cap.release()
        rabbitmq_client.close()
        if stop_event:
            stop_event.set()
            logger.info(f"Video {processor_id} - Stop event set, signaling consumer to exit")
