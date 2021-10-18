# https://stackoverflow.com/questions/49005651/how-does-asyncio-actually-work
# https://docs.python.org/3/library/select.html#select.select

from typing import BinaryIO, Coroutine, Dict, List, Tuple
import sys
import time
import select


class AsyncSleep:
    """Event to sleep until a point in time"""

    def __init__(self, until: float):
        self.until = until

    # used whenever someone ``await``s an instance of this Event
    def __await__(self):
        # yield this Event to the loop
        yield self

    def __repr__(self):
        return f"{self.__class__.__name__}, until={self.until}"


class AsyncRead:
    def __init__(self, file: BinaryIO, amount: int):
        self.file = file
        self.amount = amount
        self._buffer = b""

    def __await__(self):
        while len(self._buffer) < self.amount:
            # keep reading until `amount` of bytes have been read
            yield self
            # we only get here if ``read`` should not block
            self._buffer += self.file.read(10)
        return self._buffer

    def __repr__(self):
        return "%s(file=%s, amount=%d, progress=%d)" % (
            self.__class__.__name__,
            self.file,
            self.amount,
            len(self._buffer),
        )


def run(*coroutines: Coroutine):
    """
    Cooperatively run all `coroutines` until completion
    """

    waiting: List[Tuple[float, Coroutine]] = [
        (0, coroutine) for coroutine in coroutines
    ]

    waiting_read: Dict[BinaryIO, Coroutine] = {}

    while waiting or waiting_read:
        # Wait until the next sleep coroutine may run, or read coroutine may read
        try:
            until, coroutine = waiting.pop(0)
        except IndexError:
            continue

        to_wait = max(0.0, until - time.time())
        # `select` blocks for up to to_wait seconds to ensure we don't spin
        readable, _, _ = select.select(waiting_read.keys(), [], [], to_wait)

        if time.time() < until:
            # This is a sleep coroutine, but we haven't slept for our amount of time yet...
            if readable:
                # So, if there's readable data, get a read coroutine instead, and put in back onto waiting list
                waiting.append((until, coroutine))
                waiting.sort()
                coroutine = waiting_read.pop(readable[0])

        # Run this coroutine until it yields again or finishes (read a bit of data, or consume the sleep coroutine)
        try:
            command = coroutine.send(None)
        except StopIteration:
            continue

        # Sort coroutines by their desired suspension...
        if isinstance(command, AsyncSleep):
            waiting.append((command.until, coroutine))
            waiting.sort(key=lambda item: item[0])
        # ...Or register reads
        elif isinstance(command, AsyncRead):
            waiting_read[command.file] = coroutine


async def sleep(identifier: str = "coroutine", count: int = 5):
    for i in range(count):
        print(f"{identifier} step {i + 1} at {time.time()}")
        await AsyncSleep(time.time() + 0.1)


async def read(path, amount: int = 1024 * 32) -> None:
    print(f"read {path} at {time.time()}")
    with open(path, "rb") as file:
        result = await AsyncRead(file, amount)
    print(f"done {path} at {time.time()}")
    print(f"got {len(result)} B")


# Cooperatively run all coroutines until completion
sleep_count = int(sys.argv[1]) if len(sys.argv) > 1 else 10
run(
    read("/dev/urandom", 1024),
    sleep("background", sleep_count),
    sleep("background", sleep_count),
    sleep("background", sleep_count),
)
