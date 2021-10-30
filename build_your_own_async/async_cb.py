"""
https://www.youtube.com/watch?v=Y4Gt3Xjd7G8 (Build Your Own Async)
https://stackoverflow.com/questions/34469060/python-native-coroutines-and-send
http://www.dabeaz.com/coroutines/
https://snarky.ca/how-the-heck-does-async-await-work-in-python-3-5/
"""

import heapq
import time
from collections import deque


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


# If you want to do concurrency, you have to interract with scheduler
def countdown(n):
    # Nothing blocks in here, this function just schedules things to run later
    if n > 0:
        print("down", n)
        # time.sleep(1)
        sched.call_later(2, lambda: countdown(n - 1))


def countup(stop):
    def _run(n):
        if n < stop:
            print("up", n)
            # time.sleep(1)
            sched.call_later(1, lambda: _run(n+1))
    _run(0)


sched.call_soon(lambda: countdown(5))
sched.call_soon(lambda: countup(10))
sched.run()
