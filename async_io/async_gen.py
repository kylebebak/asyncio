"""
Async scheduler without callbacks, using generators instead.
"""

# sequential
import time
from collections import deque
from typing import Deque, Generator, Optional


class Scheduler:
    def __init__(self):
        self.ready: Deque[Generator] = deque()
        self.current: Optional[Generator] = None  # Currently executing generator

    def new_task(self, gen: Generator):
        self.ready.append(gen)

    def run(self):
        while self.ready:
            self.current = self.ready.popleft()
            # Drive as a generator
            try:
                next(self.current)  # Advance generator one step
                if self.current:
                    self.ready.append(self.current)  # Put it back on list of ready generators
            except StopIteration:
                pass


sched = Scheduler()  # Background scheduler object


def countdown(n):
    while n > 0:
        print("down", n)
        time.sleep(1)
        yield
        n -= 1


def countup(stop):
    n = 0
    while n < stop:
        print("up", n)
        time.sleep(1)
        yield
        n += 1


sched.new_task(countdown(5))
sched.new_task(countup(5))
sched.run()
