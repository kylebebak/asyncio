"""
Async scheduler without callbacks and coroutines, because asyncio depends on
callback-based code as well as coroutine-based code.

nc localhost 5000
"""

import heapq
import select
import socket
import time
from collections import deque
from typing import Callable, Deque, List, Optional, Tuple, Union


TaskFn = Union["Task", Callable]


class Scheduler:
    def __init__(self):
        self.ready: Deque[TaskFn] = deque()  # Functions read to execute
        self.sleeping: List[Tuple[float, int, TaskFn]] = []  # Sleeping functions
        self.current: Optional[TaskFn] = None  # Currently executing coroutine/task
        # This just breaks ties in prio queue
        self.sequence = 0

        self.read_waiting = {}
        self.write_waiting = {}

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

    def new_task(self, coro):
        self.ready.append(Task(coro))

    async def sleep(self, delay):
        self.call_later(delay, self.current)
        self.current = None
        await Switch()  # Switch to a new task

    def read_wait(self, fileno, func):
        # Trigger func when fileno is readable
        self.read_waiting[fileno] = func

    def write_wait(self, fileno, func):
        # Trigger func when fileno is writable
        self.write_waiting[fileno] = func

    async def recv(self, sock: socket.socket, maxbytes: int):
        self.read_wait(sock, self.current)  # Advance current task when sock is ready for reading
        self.current = None
        # Switch to new task, and when we come back it's because run method has
        #   put task back onto ready and we have data to read
        await Switch()
        return sock.recv(maxbytes)

    async def send(self, sock: socket.socket, data: bytes):
        self.write_wait(sock, self.current)
        self.current = None
        await Switch()
        return sock.send(data)

    async def accept(self, sock: socket.socket):
        self.read_wait(sock, self.current)
        self.current = None
        await Switch()
        return sock.accept()

    def run(self):
        while self.ready or self.sleeping or self.read_waiting or self.write_waiting:
            if not self.ready:

                if self.sleeping:
                    # Find nearest sleeping deadline, don't pop it off queue
                    deadline, _, func = self.sleeping[0]
                    timeout = max(deadline - time.monotonic(), 0)
                else:
                    timeout = None  # Wait forever

                # Wait for I/O; we can block event loop with select because
                #   nothing else is ready; note that select call also returns if
                #   listening socket accepts new connection, or client socket
                #   closes connection
                can_read, can_write, _ = select.select(self.read_waiting, self.write_waiting, [], timeout)

                for fileno in can_read:
                    self.ready.append(self.read_waiting.pop(fileno))
                for fileno in can_write:
                    self.ready.append(self.write_waiting.pop(fileno))

                now = time.monotonic()
                # Find any sleeping tasks that are ready and put them onto ready queue
                while self.sleeping:
                    if now > self.sleeping[0][0]:
                        self.ready.append(heapq.heappop(self.sleeping)[2])
                    else:
                        break

            while self.ready:
                # If it's a callback function, we call it; if it's a coro wrapped in Task, we advance coro one step
                func = self.ready.popleft()
                func()


def get_sched() -> Scheduler:
    """
    Singleton: https://stackoverflow.com/questions/6760685
    """
    if not hasattr(get_sched, "scheduler"):
        setattr(get_sched, "scheduler", Scheduler())
    return get_sched.scheduler


class Switch:
    """
    Wherever you see async/await, there's a yield statement underneath it
    somewhere. async/await largely exists to hide presence of yield statement.
    """

    def __await__(self):
        # Any __await__ magic method must yield at some point
        yield


class Task:
    """
    Wrapper class around coroutine, to make coroutine "look like" a callback if
    desired.
    """
    def __init__(self, coro):
        self.coro = coro

    def __call__(self):
        try:
            # Driving the coroutine as before
            sched = get_sched()
            sched.current = self
            self.coro.send(None)
            if sched.current:
                sched.ready.append(self)

        except StopIteration:
            pass


# -----


class AsyncQueue:
    """
    This class manages waiters, coordinates put and get calls so that get
    doesn't block, and instead can put callback onto waiters so that's it's
    scheduled to run immediately when put is called next.
    """
    def __init__(self):
        self.items = deque()
        self.waiting: Deque[TaskFn] = deque()  # All getters waiting for data

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


# If you want to do concurrency, you have to interract with scheduler
def countdown(n):
    # Nothing blocks in here, this function just schedules things to run later
    if n > 0:
        print("down", n)
        # time.sleep(1)
        sched.call_later(1, lambda: countdown(n - 1))


def countup(stop):
    def _run(n):
        if n < stop:
            print("up", n)
            # time.sleep(1)
            sched.call_later(1, lambda: _run(n+1))
    _run(0)


async def tcp_server(host="127.0.0.1", port=5000):
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.bind((host, port))
    lsock.listen(5)

    sched = get_sched()

    while True:
        conn, addr = await sched.accept(lsock)
        print("Connection accepted", conn, addr)
        sched.new_task(echo_handler(conn))


async def echo_handler(sock: socket.socket):
    sched = get_sched()

    while True:
        data = await sched.recv(sock, 10000)
        if not data:  # Connection closed, because client sent 0 bytes
            break
        await sched.send(sock, b"Got:" + data)
    print("Connection closed", sock)
    sock.close()


if __name__ == "__main__":
    q = AsyncQueue()
    sched = get_sched()

    # We can do callback_based programming, and async based programming
    sched.call_soon(lambda: countdown(10))
    sched.call_soon(lambda: countup(10))
    sched.new_task(producer(q, 10))
    sched.new_task(consumer(q))
    sched.new_task(tcp_server())

    # Note that all tasks must be put on loop before running it
    sched.run()
