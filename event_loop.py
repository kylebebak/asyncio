# https://stackoverflow.com/questions/49005651/how-does-asyncio-actually-work
from typing import Any, BinaryIO
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
        return "%s(until=%.1f)" % (self.__class__.__name__, self.until)


class AsyncRead:
    def __init__(self, file: BinaryIO, amount=1):
        self.file = file
        self.amount = amount
        self._buffer = b''

    def __await__(self) -> Any:
        while len(self._buffer) < self.amount:
            # keep reading until `amount` of bytes have been read
            yield self
            # we only get here if ``read`` should not block
            self._buffer += self.file.read(1)
        return self._buffer

    def __repr__(self):
        return '%s(file=%s, amount=%d, progress=%d)' % (
            self.__class__.__name__, self.file, self.amount, len(self._buffer)
        )


def run(*coroutines):
    """Cooperatively run all ``coroutines`` until completion"""
    waiting_read = {}  # Dict[file, coroutine]
    waiting = [(0, coroutine) for coroutine in coroutines]
    while waiting or waiting_read:
        # 2. wait until the next coroutine may run or read ...
        try:
            until, coroutine = waiting.pop(0)
        except IndexError:
            until, coroutine = float('inf'), None
            readable, _, _ = select.select(list(waiting_read), [], [])
        else:
            to_wait = max(0.0, until - time.time())
            readable, _, _ = select.select(list(waiting_read), [], [], to_wait)
        # ... and select the appropriate one
        if readable and time.time() < until:
            if until and coroutine:
                waiting.append((until, coroutine))
                waiting.sort()
            coroutine = waiting_read.pop(readable[0])
        # 3. run this coroutine
        try:
            command = coroutine.send(None)
        except StopIteration:
            continue
        # 1. sort coroutines by their desired suspension ...
        if isinstance(command, AsyncSleep):
            waiting.append((command.until, coroutine))
            waiting.sort(key=lambda item: item[0])
        # ... or register reads
        elif isinstance(command, AsyncRead):
            waiting_read[command.file] = coroutine


async def asleep(duration: float):
    """await that ``duration`` seconds pass"""
    await AsyncSleep(time.time() + duration)


async def sleepy(identifier: str = "coroutine", count=5):
    for i in range(count):
        print(identifier, "step", i + 1, "at %.2f" % time.time())
        await asleep(0.1)


async def ready(path, amount=1024*32) -> None:
    print('read', path, 'at', '%d' % time.time())
    with open(path, 'rb') as file:
        result = await AsyncRead(file, amount)
    print('done', path, 'at', '%d' % time.time())
    print('got', len(result), 'B')


run(sleepy('background', 5), ready('/dev/urandom', 1024*128))

run(*(sleepy(f"coroutine {j+1}") for j in range(5)))
