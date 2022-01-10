from queue import Full as QueueFullException
import multiprocessing as mp
import argparse
import pathlib
import logging
import regex
import time
import sys

import ujson
from dateutil import parser
from log_parser import rabbitmq
from log_parser import log_reader

REGEXES_DIR_PATH = pathlib.Path("./regexes").absolute()
assert REGEXES_DIR_PATH.exists(), "failed to find valid regexes directory!"

log = logging.getLogger(__file__)
stdout_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(levelname).1s [%(processName)s - %(threadName)s] | %(message)s")
stdout_handler.setFormatter(formatter)
log.setLevel(logging.DEBUG)
log.addHandler(stdout_handler)

timestamp_regex = r'^\[(?P<timestamp>[a-zA-Z0-9: ]+)\] '


def get_files():
    yield from (
        filepath
        for filepath in REGEXES_DIR_PATH.glob("*.py-regexes")
        if filepath.is_file()
    )


def get_exchange_to_regex_mappings():
    ret = dict()
    for filepath in get_files():
        with filepath.open('r') as f:
           rgx = [
               regex.compile(timestamp_regex + line.rstrip())
               for line in f.readlines()
               if len(line.rstrip()) > 0
            ]
        if len(rgx) > 0:
            ret[filepath.stem] = rgx
    return ret


def get_valid_exchanges():
    yield from (filepath.stem for filepath in get_files())


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument("--log-file", default="/log")
    p.add_argument("--number-of-lines", type=int, default=100)
    p.add_argument("--name", required=True, type=str)
    p.add_argument("--playback", default=False, action='store_true')
    args = p.parse_args()
    log.info("starting script")
    log.info(f"args={args}")
    log_path = pathlib.Path(args.log_file)
    character_name = str(args.name).lower()
    log_size_mb = round(log_path.stat().st_size * 1e-6, 2)
    log.info(f"file size mb={log_size_mb}")

    if args.playback:
        log.info("setting up playback according to inbound events")
    playback = args.playback

    known_exchanges = get_valid_exchanges()
    rabbitmq.RobustConnection.setup_exchanges(exchanges=known_exchanges)

    def process_to_rmq(message_exchange, regexps, q: mp.Queue):
        def parse_data_items(item):
            match item:
                case ['timestamp', unparsed_ts]:
                    return ['timestamp', parser.parse(unparsed_ts).timestamp()]
                case [k, ("YOU" | "You" | "you")]:
                    return k, character_name
                case ['amount', n]:
                    return 'amount', int(n)
                case ['target', target]:
                    return 'target', str(target).lower()
                case ['source', source]:
                    return 'source', str(source).lower()
                case ['modifier', modifier]:
                    return 'modifier', modifier.split()
            return item

        def parse_message_data(data):
            output = dict(
                parse_data_items([k, v.strip()])
                for (k, v) in data.items()
            )
            output.setdefault('character_name', character_name)
            if exchange == 'combat':
                output.setdefault('amount', 0)
                output['successful'] = bool(output.get('amount') > 0)
            output['exchange'] = exchange
            return output

        current_timestamp = None
        while True:
            if unparsed_line := q.get():
                for r in regexps:
                    if match := r.search(unparsed_line):
                        groups = match.groupdict()
                        data = parse_message_data(groups)

                        if playback and current_timestamp:
                            time_to_sleep = data.get('timestamp') - current_timestamp
                            if time_to_sleep > 0.0:
                                time.sleep(time_to_sleep)
                        current_timestamp = data.get('timestamp')

                        json = ujson.dumps(data)
                        rabbitmq.RobustConnection.send(message_exchange, json)

    exchanges, regexes = zip(*get_exchange_to_regex_mappings().items())
    queues = [mp.Queue(100_000) for _ in exchanges]
    processes = []

    for exchange, rgxs, queue in zip(exchanges, regexes, queues):
        process = mp.Process(
            target=process_to_rmq,
            args=(exchange, rgxs, queue),
            daemon=True
        )
        process.start()
        processes.append(process)

    log_lines = log_reader.iterate_log_lines(
        file_path=log_path,
        n=args.number_of_lines
    )

    print("starting loop, CTRL+C to stop...\n")
    try:
        for i, line in enumerate(log_lines, start=1):
            for exchanes, queue in zip(exchanges, queues):
                try:
                    queue.put(line, block=False)
                    if i % 1_000 == 0:
                        log.info(f"exchange - records={i}")
                    
                except QueueFullException as err:
                    log.error("queue full error. Ignoring record")
                    log.warning(f"queue size={queue.qsize()}")
                    log.error(err)
                    time.sleep(0.2)
    except KeyboardInterrupt as err:
        ...

    print("shutting down processes")
    for process in processes:
        if process.is_alive():
            process.terminate()
    print("shutting down rmq connection")
    rabbitmq.RobustConnection.close()
    print("finished")

