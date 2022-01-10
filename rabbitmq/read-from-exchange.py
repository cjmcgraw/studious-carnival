#! /usr/bin/env python3
from uuid import uuid4 as uuid
import argparse

import ujson
import pika

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument("--exchange", required=True)
    p.add_argument("--pretty-print", default=False, action='store_true')
    args = p.parse_args()

    conn = pika.BlockingConnection(
        pika.ConnectionParameters('localhost')
    )
    channel = conn.channel()
    channel.exchange_declare(exchange=args.exchange, exchange_type='fanout')
    queue_name = f"manual_{uuid().hex}"
    queue = channel.queue_declare(queue=queue_name, exclusive=True)
    channel.queue_bind(exchange=args.exchange, queue=queue.method.queue)

    def print_message(ch, method, properties, body):
        output = ujson.loads(body)
        try:
            if args.pretty_print:
                s = ujson.dumps(output, indent=4)
                print(s)
                print('----------------------')
            else:
                print(ujson.dumps(output))
        except Exception as err:
            print(f"failed to json load ${body}")
            print(err)
            print('----------------------')

    channel.basic_consume(queue=queue_name, auto_ack=True, on_message_callback=print_message)
    channel.start_consuming()
