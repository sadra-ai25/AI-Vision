import pika
import logging
import time

logger = logging.getLogger(__name__)
from config.config import settings

class RabbitMQClient:
    def __init__(self, host, port, user, password):
        self.credentials = pika.PlainCredentials(user, password)
        # heartbeat now an int
        self.parameters = pika.ConnectionParameters(
            host=host,
            port=port,
            credentials=self.credentials,
            heartbeat=settings.RABBITMQ_HEARTBEAT,
            blocked_connection_timeout=300
        )
        self.connection = None
        self.channel = None

    def connect(self):
        try:
            self.connection = pika.BlockingConnection(self.parameters)
            self.channel = self.connection.channel()
            # ensure consumer prefetch so we don't overload consumer
            self.channel.basic_qos(prefetch_count=1)
            logger.info("Connected to RabbitMQ, prefetch_count=1")
        except Exception as e:
            logger.error(f"RabbitMQ connection failed: {e}")
            time.sleep(5)
            raise

    def declare_queue(self, queue_name):
        if not self.connection or self.connection.is_closed:
            self.connect()
        # Set max length and drop oldest when limit is reached
        args = {
            'x-max-length': settings.RABBITMQ_QUEUE_MAXLEN,
            'x-overflow': 'drop-head'
        }
        self.channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments=args
        )

    def publish(self, queue_name, message):
        self.declare_queue(queue_name)
        try:
            self.channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    expiration=str(int(60000))
                )
            )
        except pika.exceptions.UnroutableError:
            logger.warning(f"Queue {queue_name} full, dropping frame.")

    def basic_get(self, queue_name):
        try:
            self.declare_queue(queue_name)
            method_frame, header_frame, body = self.channel.basic_get(queue_name)
            if method_frame:
                self.channel.basic_ack(method_frame.delivery_tag)
                return body
            return None
        except Exception as e:
            logger.error(f"Error getting message: {e}")
            self.connect()
            return None

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
