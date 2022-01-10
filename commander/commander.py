from dataclasses import dataclass


from ahk import AHK
import ujson
import pika
import sys
import os

ahk = AHK()
RABBITMQ_HOST = "localhost"
RABBITMQ_EXCHANGE = "client_logs"
RABBITMQ_QUEUE = "Sszalissar"

rmq_connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=RABBITMQ_HOST)
)
rmq_channel = rmq_connection.channel()
result = rmq_channel.queue_declare(queue=RABBITMQ_QUEUE)
rmq_channel.queue_bind(exchange=RABBITMQ_EXCHANGE, queue=result.method.queue)

@dataclass
class GameActor:
    name: str
    damage_dealt: list = [0] * 20
    damage_recieved: list = [0] * 20
    


def report_dps(ch, method, properties, body):
    data = ujson.loads(body)

rmq_channel.basic_consume(queue=result.method.queue, on_message_callback=callback, auto_ack=True)
rmq_channel.start_consuming()
