# https://stackoverflow.com/questions/49005651/how-does-asyncio-actually-work
import time


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


async def asleep(duration: float):
    """await that ``duration`` seconds pass"""
    await AsyncSleep(time.time() + duration)


def run(*coroutines):
    """Cooperatively run all ``coroutines`` until completion"""
    # store wake-up-time and coroutines
    waiting = [(0, coroutine) for coroutine in coroutines]
    while waiting:
        # 2. pick the first coroutine that wants to wake up
        until, coroutine = waiting.pop(0)
        # 3. wait until this point in time
        to_wait = max(0.0, until - time.time())
        time.sleep(to_wait)
        print(round(to_wait, 2))
        # 4. run this coroutine
        try:
            command = coroutine.send(None)
        except StopIteration:
            continue
        # 1. sort coroutines by their desired suspension
        if isinstance(command, AsyncSleep):
            waiting.append((command.until, coroutine))
            waiting.sort(key=lambda item: item[0])


async def sleepy(identifier: str = "coroutine", count=5):
    for i in range(count):
        print(identifier, "step", i + 1, "at %.2f" % time.time())
        await asleep(0.1)


run(*(sleepy(f"coroutine {j+1}") for j in range(5)))
