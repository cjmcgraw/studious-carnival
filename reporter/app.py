from uuid import uuid4 as uuid
import random as r
import logging
import time
import sys
import os
import asyncio

logging.basicConfig(
    level=logging.DEBUG,
    stream=sys.stdout,
)

from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS

from aio_pika import connect_robust, IncomingMessage, ExchangeType

import ujson

log = logging.getLogger(__file__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler(sys.stdout))

INFLUXDB_URL = os.environ['INFLUXDB_URL']
INFLUXDB_ORG = os.environ['INFLUXDB_ORG']
INFLUXDB_TOKEN = os.environ['INFLUXDB_TOKEN']

RABBITMQ_HOST = os.environ['RABBITMQ_HOST']

log.info(f"influxdb_url={INFLUXDB_URL} influxdb_org={INFLUXDB_ORG}")
influx_client = InfluxDBClient(INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
influx_buckets = influx_client.buckets_api()
if not influx_buckets.find_bucket_by_name("combat"):
    influx_buckets.create_bucket(bucket_name="combat", org_id=INFLUXDB_ORG)

influx_writer = influx_client.write_api(write_options=SYNCHRONOUS)
log.info("successfully setup influxdb client")

ignored_record_keys = {"timestamp", "exchange", "amount"}

async def on_message(msg: IncomingMessage):
    async with msg.process():
        try:
            data = ujson.loads(msg.body)
            exchange = data['exchange']
            valid_keys = set(data.keys()).difference(ignored_record_keys)
            point = Point(exchange)
            for key in valid_keys:
                point = point.tag(key, data[key])
            point = point.field("amount", data['amount'])
            result = influx_writer.write(bucket=exchange, record=point)
        except Exception as err:
            log.error(err)
            log.warning(f"ignoring data at {msg}")
        

async def main(loop):
    connection = await connect_robust(f"amqp://{RABBITMQ_HOST}", loop=loop)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    exchange = await channel.declare_exchange("combat", ExchangeType.FANOUT)
    queue = await channel.declare_queue(exclusive=True)
    await queue.bind(exchange)
    await queue.consume(on_message)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(main(loop))
    print("waiting for logs... To exit press CTRL+C")
    loop.run_forever()
