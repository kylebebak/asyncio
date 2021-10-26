# Producer-consumer problem, with no threads

import time
import heapq
from collections import deque
from typing import Callable, Deque


class Scheduler:
    def __init__(self):
        self.ready = deque()  # Functions read to execute
        self.sleeping = []  # Sleeping functions
        # This just breaks ties in prio queue
        self.sequence = 0

    def call_soon(self, func):
        self.ready.append(func)

    def call_later(self, delay, func):
        """
        Scheduler can handle time management as well.
        """
        self.sequence += 1
        deadline = time.monotonic() + delay
        # Priority queue
        heapq.heappush(self.sleeping, (deadline, self.sequence, func))  # Maintain sorted order by closest deadline

    def run(self):
        while self.ready or self.sleeping:
            if not self.ready:
                # Find nearest deadline
                deadline, _, func = heapq.heappop(self.sleeping)
                delta = deadline - time.monotonic()
                if delta > 0:
                    time.sleep(delta)
                self.ready.append(func)

            while self.ready:
                func = self.ready.popleft()
                func()


sched = Scheduler()

# -----


class AsyncQueue:
    """
    This class manages waiters, coordinates put and get calls so that get
    doesn't block, and instead can put callback onto waiters so that's it's
    scheduled to run immediately when put is called next.
    """
    def __init__(self):
        self.items = deque()
        self.waiting: Deque[Callable] = deque()  # All getters waiting for data

    def put(self, item):
        self.items.append(item)
        if self.waiting:
            func = self.waiting.popleft()
            # Do we call this right away? No; instead, interact with scheduler
            sched.call_soon(func)

            # func() --> don't do this, we might get deep calls, recursion, etc

    def get(self, callback: Callable):
        # Wait until an item is available, then return it, but do this without blocking
        if self.items:
            callback(self.items.popleft())
        else:
            # If no data is avaiable we go into waiting queue and walk away
            self.waiting.append(lambda: self.get(callback))


def producer(q: AsyncQueue, count: int):
    def _run(n):
        if n < count:
            print("Producing", n)
            q.put(n)
            sched.call_later(1, lambda: _run(n + 1))  # So producer doesn't block when it "sleeps"
        else:
            print("Producer done")
            q.put(None)  # Put sentinel value to tell consumer to shut down when producer is done
    _run(0)


def consumer(q: AsyncQueue):
    def _run(item):
        if item is None:
            print("Consumer done")
        else:
            print("Consuming", item)
            sched.call_soon(lambda: consumer(q))
    # Call get with callback; callback calls consumer again to consume another
    #   item, until callback gets None (producer is finished)
    q.get(callback=_run)


q = AsyncQueue()
sched.call_soon(lambda: producer(q, 10))
sched.call_soon(lambda: consumer(q))
sched.run()
