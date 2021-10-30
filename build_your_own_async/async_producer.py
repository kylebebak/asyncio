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
        await Switch()  # Switch tasks (this basically `yield`s underneath)

    def new_task(self, coro: Coroutine):
        self.ready.append(coro)

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
                    # Put it back on list of ready coroutines, unless calling send has set current coroutine to None
                    self.ready.append(self.current)
            except StopIteration:
                pass


sched = Scheduler()  # Background scheduler object


class Switch:
    """
    Wherever you see async/await, there's a yield statement underneath it
    somewhere. async/await largely exists to hide presence of yield statement.
    """

    def __await__(self):
        # Any __await__ magic method must yield at some point
        yield


class AsyncQueue:
    """
    This class manages waiters, coordinates put and get calls so that get
    doesn't block, and instead can put callback onto waiters so that's it's
    scheduled to run immediately when put is called next.
    """
    def __init__(self):
        self.items = deque()
        self.waiting: Deque[Coroutine] = deque()  # All getters waiting for data

    def put(self, item):
        self.items.append(item)
        if self.waiting:
            # Take first waiting coroutine and append it to scheduler's ready coroutines
            sched.ready.append(self.waiting.popleft())

    async def get(self):
        if not sched.current:
            return

        # Wait until an item is available, then return it, but do this without blocking
        if not self.items:
            # Wait for an item
            self.waiting.append(sched.current)  # Put current coroutine into waiting queue
            # Have this coroutine "disappear" from scheduler; queue knows it's waiting, but sched doesn't know about it
            sched.current = None
            await Switch()  # Yield and switch to another task
        # This coroutine won't resume until we put it back on scheduler (this happens in call to put)
        return self.items.popleft()


async def producer(q, count):
    for n in range(count):
        print("Producing", n)
        q.put(n)
        await sched.sleep(1)
    print("Producer done")
    q.put(None)  # Signal to consumer to shut down


async def consumer(q):
    while True:
        item = await q.get()
        if item is None:
            break
        print("Consuming", item)
    print("Consumer done")


if __name__ == "__main__":
    q = AsyncQueue()
    sched.new_task(producer(q, 5))
    sched.new_task(consumer(q))
    sched.run()
