async def ca():
    yield 1
    yield 2
    yield 3


async def cb():
    yield 4
    yield 5
    yield 6


def loop(*coroutines):
    while True:
        for c in coroutines:
            try:
                print(next(c))
            except StopIteration:
                return


loop(ca(), cb())
