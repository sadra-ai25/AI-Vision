
from fastapi import FastAPI, UploadFile, File, Form
from threading import Thread, Event
import tempfile
import time
import os
from pydantic import BaseModel
from capture.producer import camera_producer, video_producer
from processing.frame_consumer import frame_consumer
from config.config import settings

app = FastAPI()
active_processors = {}

class CameraConfig(BaseModel):
    camera_id: str

@app.on_event("startup")
async def startup_event():
    for camera_id in settings.CAMERAS.keys():
        if camera_id in active_processors:
            continue
        stop_event = Event()
        producer_thread = Thread(
            target=camera_producer,
            args=(camera_id, stop_event)
        )
        consumer_thread = Thread(
            target=frame_consumer,
            args=(camera_id, None, 'camera', stop_event)
        )
        producer_thread.start()
        consumer_thread.start()
        active_processors[camera_id] = {
            "producer_thread": producer_thread,
            "consumer_thread": consumer_thread,
            "stop_event": stop_event
        }
    print(f"Started processing for cameras: {list(settings.CAMERAS.keys())}")

@app.post("/stop/{camera_id}")
async def stop_camera(camera_id: str):
    if camera_id not in active_processors:
        return {"error": "Camera not found"}
    proc = active_processors[camera_id]
    proc["stop_event"].set()
    proc["producer_thread"].join(timeout=5)
    proc["consumer_thread"].join(timeout=5)
    del active_processors[camera_id]
    return {"status": "stopped", "camera_id": camera_id}

@app.post("/start/video")
async def start_video(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
        temp_file.write(await file.read())
        temp_path = temp_file.name
    processor_id = f"video_{int(time.time())}"
    stop_event = Event()
    producer_thread = Thread(
        target=video_producer,
        args=(temp_path, processor_id, stop_event)
    )
    consumer_thread = Thread(
        target=frame_consumer,
        args=(processor_id, temp_path, 'video', stop_event)
    )
    producer_thread.start()
    consumer_thread.start()
    active_processors[processor_id] = {
        "producer_thread": producer_thread,
        "consumer_thread": consumer_thread,
        "stop_event": stop_event,
        "temp_file": temp_path
    }
    return {"status": "video processing started", "processor_id": processor_id}