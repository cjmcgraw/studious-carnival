import pathlib
import logging
import sys

import sh

log = logging.getLogger(__file__)
stdout_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(levelname).1s [%(processName)s - %(threadName)s] | %(message)s")
stdout_handler.setFormatter(formatter)
log.setLevel(logging.DEBUG)
log.addHandler(stdout_handler)

def iterate_log_lines(file_path:pathlib.Path, n:int = 0, **kwargs):
    """Reads the file in line by line

        dev note: One of the best featuers of this functions is we can use efficient
        unix style operations. Because we know we are inside of a unix container
        there should be no problem relying on GNU tail directly.
    """
    abs_path = file_path.absolute()
    def get_tail_iter(replay=0):
        return sh.tail("-n", replay, "-f", str(abs_path), _iter=True)
            
    tail_itr = get_tail_iter(replay=n)
    while True:
        try:
            for line in tail_itr:
                yield line.strip()
        except KeyboardInterrupt as err:
            raise err
        except Exception as err:
            log.error(err)
            log.warning("continuing tail of file")
            tail_itr = get_tail_iter(replay=0)
