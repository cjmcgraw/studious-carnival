import logging
import sys
import os

import pika

log = logging.getLogger(__file__)
stdout_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(levelname).1s [%(processName)s - %(threadName)s] | %(message)s")
stdout_handler.setFormatter(formatter)
log.setLevel(logging.DEBUG)
log.addHandler(stdout_handler)

RABBITMQ_HOSTS = os.environ['RABBITMQ_HOSTS_CSV'].split(',')
assert len(RABBITMQ_HOSTS) > 0, "must provide valid RABBITMQ_HOSTS_CSV envvar"
log.info(f"setting up rabbitmq hosts: {RABBITMQ_HOSTS}")


class RobustConnection():
    connection = None
    channel = None

    @classmethod
    def get_channel(cls):
        con = cls.connection
        chn = cls.channel
        if not con or not con.is_open:
            log.warning("setting up rmq connection")
            cls.connection = pika.BlockingConnection([
                pika.ConnectionParameters(host=h)
                for h in RABBITMQ_HOSTS if h
            ])
            log.warning("successfully setup rmq connection")

        if not chn or not chn.is_open:
            log.warning("retrieving rmq channel")
            cls.channel = cls.connection.channel()
            log.warning("successfully setup rmq channel")
        return cls.channel

    @classmethod
    def close(cls):
        con = cls.connection
        chn = cls.channel
        try:
            if chn and chn.is_open:
                chn.close()
        except Exception as err:
            log.error(err)

        try:
            if con and con.is_open:
                con.close()
        except Exception as err:
            log.error(err)

    @classmethod
    def setup_exchanges(cls, exchanges, **kwargs):
        kwargs.setdefault("exchange_type", "fanout")
        chn = cls.get_channel()
        for exchange in exchanges:
            log.info(f"setting up rabbitmq exchange: {exchange}")
            chn.exchange_declare(exchange=exchange, **kwargs)

    @classmethod
    def send(cls, exchange, json, retries=5, **kwargs):
        try:
            chn = cls.get_channel()
            chn.basic_publish(
                exchange=exchange,
                routing_key=exchange,
                body=json,
            )
        except Exception as err:
            log.error(err)
            if retries <= 0:
                raise err
            cls.send(exchange, json, retries=retries - 1, **kwargs)

