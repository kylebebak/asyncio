# Producer-consumer problem

import queue
import time
import threading


def producer(q, count):
    for n in range(count):
        print("Producing", n)
        q.put(n)
        time.sleep(1)

    q.put(None)  # Insert sentinel value as signal to consumer to shut down when producer is done


def consumer(q):
    while True:
        item = q.get()
        if item is None:
            # If we hit sentinel value, nothing left on queue
            break
        print("Consuming", item)
    print("Consumer done")


q = queue.Queue()  # Thread-safe queue
threading.Thread(target=producer, args=(q, 10)).start()
threading.Thread(target=consumer, args=(q,)).start()
