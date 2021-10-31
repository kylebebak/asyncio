"""
Async scheduler without callbacks, using coroutines instead.
"""

# sequential
import time
from collections import deque
import heapq
from typing import Deque, Coroutine, List, Optional, Tuple


class Scheduler:
    def __init__(self):
        self.ready: Deque[Coroutine] = deque()
        self.sleeping: List[Tuple[float, int, Coroutine]] = []
        self.current: Optional[Coroutine] = None  # Currently executing coroutine
        self.sequence = 0  # For breaking ties when sorting heap

    async def sleep(self, delay: float):
        # The current coroutine wants to sleep
        if self.current is None:
            return

        deadline = time.monotonic() + delay
        self.sequence += 1
        # Coroutine puts itself onto sleeping queue
        heapq.heappush(self.sleeping, (deadline, self.sequence, self.current))
        self.current = None  # This ensures run method doesn't put this coroutine back into ready queue
        await switch()  # Switch tasks (this basically `yield`s underneath)

    def new_task(self, gen: Coroutine):
        self.ready.append(gen)

    def run(self):
        while self.ready or self.sleeping:
            if not self.ready:
                # There's something sleeping, but nothing ready
                deadline, _, coro = heapq.heappop(self.sleeping)  # Get sleeping coro with soonest deadline
                delta = deadline - time.monotonic()
                if delta > 0:
                    # We can block event loop with sleep because nothing else is ready
                    time.sleep(delta)
                # After we've slept this coro is ready
                self.ready.append(coro)

            self.current = self.ready.popleft()
            # Drive as a coroutine
            try:
                self.current.send(None)  # Advance coroutine one step (use instead of `next`)
                if self.current:
                    self.ready.append(self.current)  # Put it back on list of ready coroutines
            except StopIteration:
                pass


sched = Scheduler()  # Background scheduler object


class Awaitable:
    """
    Wherever you see async/await, there's a yield statement underneath it
    somewhere. async/await largely exists to hide presence of yield statement.
    """

    def __await__(self):
        # Any __await__ magic method must yield at some point
        yield


def switch():
    """
    This just executes a yield statement
    """
    return Awaitable()


async def countdown(n):
    while n > 0:
        print("down", n)
        await sched.sleep(2)
        n -= 1


async def countup(stop):
    n = 0
    while n < stop:
        print("up", n)
        await sched.sleep(1)
        n += 1


if __name__ == "__main__":
    sched.new_task(countdown(3))
    sched.new_task(countup(6))
    sched.run()
