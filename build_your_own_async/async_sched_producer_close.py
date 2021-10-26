# Producer-consumer problem, with no threads
# Note that we're already in callback hell with this here, it's very hard to reason about

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


class QueueClosed(Exception):
    pass


# Serves same purpose as Future object in asyncio
class Result:
    def __init__(self, value=None, exc=None):
        self.value = value
        self.exc = exc

    def result(self):
        if self.exc:
            raise self.exc
        else:
            return self.value


class AsyncQueue:
    """
    This class manages waiters, coordinates put and get calls so that get
    doesn't block, and instead can put callback onto waiters so that's it's
    scheduled to run immediately when put is called next.
    """
    def __init__(self):
        self.items = deque()
        self.waiting: Deque[Callable] = deque()  # All getters waiting for data
        self._closed = False  # Can queue be used anymore? We'll do this instead of weird hack with putting None sentinel value

    def close(self):
        # We won't produce more data after this (no more queue.put), but queue.get should be OK (we want to get pending items off of queue)
        self._closed = True
        if self.waiting and not self.items:
            for func in self.waiting:
                sched.call_soon(func)

    def put(self, item):
        if self._closed:
            raise QueueClosed()

        self.items.append(item)
        if self.waiting:
            func = self.waiting.popleft()
            # Do we call this right away? No; instead, interact with scheduler
            sched.call_soon(func)

            # func() --> don't do this, we might get deep calls, recursion, etc

    def get(self, callback: Callable):
        # Wait until an item is available, then return it, but do this without blocking
        # Question: How does a closed queue interact with get()
        if self.items:
            callback(Result(value=self.items.popleft()))  # Still runs if closed, "good" result
        else:
            # If no data is avaiable we go into waiting queue and walk away
            if self._closed:
                callback(Result(exc=QueueClosed()))  # Error result
            else:
                self.waiting.append(lambda: self.get(callback))


def producer(q: AsyncQueue, count: int):
    def _run(n):
        if n < count:
            print("Producing", n)
            q.put(n)
            sched.call_later(1, lambda: _run(n + 1))  # So producer doesn't block when it "sleeps"
        else:
            print("Producer done")
            q.close()
    _run(0)


def consumer(q: AsyncQueue):
    def _run(result: Result):
        try:
            item = result.result()
        except QueueClosed:
            print("Consumer done")
        else:
            print("Consuming", item)
            sched.call_soon(lambda: consumer(q))
    # Call get with callback; callback calls consumer again to consume another
    #   item, until callback gets None (producer is finished)
    q.get(callback=_run)


q = AsyncQueue()
sched.call_soon(lambda: producer(q, 3))
sched.call_soon(lambda: consumer(q))
sched.run()
