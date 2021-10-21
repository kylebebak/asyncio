import heapq
import types
import time
from typing import Coroutine


class Task:
    """
    Represent how long a coroutine should wait before starting again.

    Comparison operators are implemented for use by heapq. Two-item tuples
    unfortunately don't work because when the times are equal, comparison falls
    to the coroutine and they don't implement comparison methods, triggering an
    exception.

    Think of this as being like asyncio.Task/curio.Task.
    """

    def __init__(self, wait_until: float, coro: Coroutine):
        self.coro = coro
        self.wait_until = wait_until

    def __eq__(self, other: "Task"):
        return self.wait_until == other.wait_until

    def __lt__(self, other: "Task"):
        return self.wait_until < other.wait_until


class SleepingLoop:
    """
    An event loop focused on delaying execution of coroutines.

    Think of this as being like asyncio.BaseEventLoop/curio.Kernel.
    """

    def __init__(self, *coros: Coroutine):
        self._new = coros
        self._waiting: list[Task] = []

    def run_until_complete(self):
        # Start all the coroutines (until sleep hits first yield)
        for coro in self._new:
            wait_for: float = coro.send(None)
            heapq.heappush(self._waiting, Task(wait_for, coro))

        # Keep running until there is no more work to do.
        while self._waiting:
            before = time.time()
            # Get the coroutine with the soonest resumption time (smallest waiting value)
            task = heapq.heappop(self._waiting)

            if before < task.wait_until:
                # We're ahead of schedule; wait until it's time to resume.
                time.sleep(task.wait_until - before)
                after = time.time()
            else:
                after = before

            try:
                # It's time to resume the coroutine. Send in how much time we actually waited for coro
                wait_until: float = task.coro.send(after)
                heapq.heappush(self._waiting, Task(wait_until, task.coro))
            except StopIteration:
                # The coroutine is done.
                pass


@types.coroutine
def sleep(seconds):
    """
    Pause a coroutine for the specified number of seconds.

    Think of this as being like asyncio.sleep()/curio.sleep().
    """
    before = time.time()
    wait_until = before + seconds
    # Make all coroutines on the call stack pause; the need to use `yield`
    # necessitates this be generator-based and not an async-based coroutine.
    actual = yield wait_until
    # Resume the execution stack, sending back how long we actually waited.
    return actual - before


async def countdown(label, length, *, delay=0):
    """
    Countdown a launch for `length` seconds, waiting `delay` seconds.

    This is what a user would typically write.
    """
    print(f"{label} waiting {delay} seconds before starting countdown")
    delta = await sleep(delay)
    print(f"{label} starting after waiting {delta}")

    while length:
        print(label, "T-minus", length)
        waited = await sleep(1)
        print("waited", waited)
        length -= 1
    print(label, "lift-off!")


def main():
    """
    Start the event loop, counting down 3 separate launches.

    This is what a user would typically write.
    """
    before = time.time()
    loop = SleepingLoop(countdown("A", 5), countdown("B", 4, delay=2))
    loop.run_until_complete()
    print("Total elapsed time is", time.time() - before)


if __name__ == "__main__":
    main()
