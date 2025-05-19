from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    DB_SERVER: str
    DB_NAME: str
    USERNAME: str
    PASSWORD: str
    CAMERAS: dict = {
        "camera1": {
            "rtsp": "rtsp://A:Aa.123456@172.16.16.29:554/cam/realmonitor?channel=1&subtype=0",
            "bbox": {"x_min": 823, "y_min": 442, "x_max": 1228, "y_max": 936},
            "counting_line_x": 1130
        },

        "camera2": {
            "rtsp": "rtsp://A:Aa.123456@172.16.16.28:5554/cam/realmonitor?channel=1&subtype=0",
            "bbox": {"x_min": 2363, "y_min": 659, "x_max": 2799, "y_max": 1216},
            "counting_line_x": 2710
        }
    }
    VIDEOS: dict = {
        "video": {
            "path": "./sample/cam1_2.mp4",
            "bbox": {"x_min": 395, "y_min": 154, "x_max": 532, "y_max": 375},
            "counting_line_x": 525
        }
    }
    DEFAULT_BBOX: dict = {"x_min": 395, "y_min": 154, "x_max": 532, "y_max": 375}
    DEFAULT_COUNTING_LINE_X: int = 525  
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASS: str = "guest"
    RABBITMQ_HEARTBEAT: int = 600
    RABBITMQ_QUEUE_MAXLEN: int = 1000
    FRAME_RATE: int = 5

    FRAMES_PATH: str = "output/frames"
    LOG_PATH: str = "output/logs/barcode_log.csv"
    CROPPED_IMAGES_PATH: str = "output/cropped_images"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()