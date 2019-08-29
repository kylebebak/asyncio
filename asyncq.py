import asyncio
import os
import random
import time


async def randsleep(caller: str) -> None:
    i = random.randint(0, 2)
    print(f"{caller} sleeping for {i} seconds.")
    await asyncio.sleep(i)


async def produce(name: int, q: asyncio.Queue) -> None:
    while True:  # Synchronous loop for each single producer
        await randsleep(f"Producer {name}")
        i = os.urandom(5).hex()
        t = time.perf_counter()
        await q.put((i, t))
        print(f"Producer {name} added <{i}> to queue.")


async def consume(q: asyncio.Queue) -> None:
    while True:
        i, t = await q.get()
        now = time.perf_counter()
        print(f"Consumer got element <{i}> in {now-t:0.5f} seconds.")
        q.task_done()


async def main() -> None:
    q: asyncio.Queue = asyncio.Queue()
    producers = [asyncio.create_task(produce(n, q)) for n in range(5)]
    consumer = asyncio.create_task(consume(q))
    await asyncio.gather(*producers)
    await q.join()  # Implicitly awaits consumer, too
    consumer.cancel()


if __name__ == "__main__":
    random.seed(444)
    start = time.perf_counter()
    asyncio.run(main())
    elapsed = time.perf_counter() - start
    print(f"Program completed in {elapsed:0.5f} seconds.")
