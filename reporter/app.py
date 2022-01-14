from typing import Union
from uuid import uuid4 as uuid
import dataclasses
import logging
import asyncio
import time
import sys
import os

from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import InfluxDBClient, Point
from aio_pika import connect_robust, IncomingMessage, ExchangeType
import betterproto as proto
import redis

from protos import events

log = logging.getLogger(__file__)
stdout_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(levelname).1s [%(processName)s - %(threadName)s] | %(message)s")
stdout_handler.setFormatter(formatter)
log.setLevel(os.environ.get("PYTHON_LOG_LEVEL", "INFO"))
log.addHandler(stdout_handler)

INFLUXDB_URL = os.environ['INFLUXDB_URL']
INFLUXDB_ORG = os.environ['INFLUXDB_ORG']
INFLUXDB_TOKEN = os.environ['INFLUXDB_TOKEN']
REDIS_HOST = os.environ['REDIS_HOST']
RABBITMQ_HOST = os.environ['RABBITMQ_HOST']

log.info(f"redis_host={REDIS_HOST}")
r = redis.Redis(host=REDIS_HOST, port=6379, db=0)
r.ping()

log.info(f"influxdb_url={INFLUXDB_URL} influxdb_org={INFLUXDB_ORG}")
influx_client = InfluxDBClient(INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

attempts = 10
log.info("waiting on influxdb to pick up...")
while not influx_client.ping():
    if attempts <= 0:
        raise ValueError("Failed to connect to influxdb")
    time.sleep(1 * (1 - 10/attempts))
log.info("successfully found influxdb")

influx_buckets = influx_client.buckets_api()
if not influx_buckets.find_bucket_by_name("combat"):
    influx_buckets.create_bucket(bucket_name="combat", org_id=INFLUXDB_ORG)

influx_writer = influx_client.write_api(write_options=SYNCHRONOUS)
log.info("successfully setup influxdb client")

exchanges = []
MetadataType = Union[
    events.CombatMetadata,
    events.HealingMetadata,
    events.SupportMetadata,
    events.GroupMetadata
]

def extract_event_data(body: bytes) -> tuple[events.Event, str, MetadataType]:
    event = events.Event.FromString(body)
    name, metadata = proto.which_one_of(event, 'metadata')
    return event, name, metadata


async def process_into_influx(msg: IncomingMessage):
    async with msg.process():
        try:
            exchange = msg.exchange
            event, name, metadata = extract_event_data(msg.body)

            point = Point(name)
            for field in dataclasses.fields(metadata):
                point = point.tag(
                    key=field.name,
                    value=getattr(metadata, field.name)
                )

            match name:
                case "combat" | "healing":
                    point = point.field("amount", metadata.amount)
                    influx_writer.write(bucket=exchange, record=point)
                case _:
                    log.warning(f"ignoring unknown message type: {name}")

        except Exception as err:
            log.error(err)
            log.warning(f"ignoring data at {msg}")


async def track_outbound_dps(msg: IncomingMessage):
    allowed_character_names = {"sszalissar"}
    async with msg.process():
        try:
            event, name, metadata = extract_event_data(msg.body)
            created_ts = int(time.mktime(event.created.timetuple()))

            match name:
                case "combat":
                    key = None
                    if metadata.target in allowed_character_names:
                        key = f"{metadata.target}_damage_outgoing_{created_ts}"
                    elif metadata.source in allowed_character_names:
                        key = f"{metadata.source}_damage_incoming_{created_ts}"
                    if key and metadata.amount > 0:
                        r.incrby(key, metadata.amount)
                        r.expire(key, 60)
                case "healing":
                    key = None
                    if metadata.target in allowed_character_names:
                        key = f"{metadata.target}_healing_incoming_{created_ts}"
                    if key and metadata.amount > 0:
                        r.incrby(key, metadata.amount)
                        r.expire(key, 60)

        except Exception as err:
            log.error(err)
            log.warning(f"ignoring data at {msg}")


async def main(loop):
    connection = await connect_robust(f"amqp://{RABBITMQ_HOST}", loop=loop)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1_000)
    exchange = await channel.declare_exchange("combat", ExchangeType.FANOUT)

    fns = [
        process_into_influx,
        track_outbound_dps
    ]
    for fn in fns:
        queue = await channel.declare_queue(name=uuid().hex, exclusive=True)
        await queue.bind(exchange)
        await queue.consume(fn)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(main(loop))
    print("waiting for logs... To exit press CTRL+C")
    loop.run_forever()
