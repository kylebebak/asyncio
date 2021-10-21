# https://snarky.ca/how-the-heck-does-async-await-work-in-python-3-5/

# Let's summarize all of this into simpler terms. Defining a method with async
# def makes it a coroutine. The other way to make a coroutine is to flag a
# generator with types.coroutine -- technically the flag is the
# CO_ITERABLE_COROUTINE flag on a code object -- or a subclass of
# collections.abc.Coroutine. You can only make a coroutine call chain pause with
# a generator-based coroutine.

# An awaitable object is either a coroutine or an object that defines
# __await__() -- technically collections.abc.Awaitable -- which returns an
# iterator that is not a coroutine. An await expression is basically yield from
# but with restrictions of only working with awaitable objects (plain generators
# will not work with an await expression). An async function is a coroutine that
# either has return statements -- including the implicit return None at the end
# of every function in Python -- and/or await expressions (yield expressions are
# not allowed). The restrictions for async functions is to make sure you don't
# accidentally mix and match generator-based coroutines with other generators
# since the expected use of the two types of generators are rather different.

from typing import Iterator
import asyncio


def lazy_range(up_to: int):
    """
    Generator to return the sequence of integers from 0 to up_to, exclusive.
    """
    index = 0
    while index < up_to:
        yield index
        index += 1


def jumping_range(up_to: int):
    """
    Generator for the sequence of integers from 0 to up_to, exclusive.

    Sending a value into the generator will shift the sequence by that amount.
    """
    index = 0
    while index < up_to:
        sent = yield index
        jump = 0

        if sent is None:
            jump = 1
        if type(sent) is int:
            jump = sent
        if type(sent) is tuple:
            jump, new_index = sent
            index = new_index

        index += jump


def yield_from(gen: Iterator):
    yield from gen


def bt():
    yield 10
    return 20


def tp():
    v = yield from bt()
    yield v + 1
    return v + 1


g = tp()
next(g)
next(g)
next(g)


def bottom():
    # Returning the yield lets the value that goes up the call stack from top->middle->bottom come back down bottom->middle->top
    v = yield 42
    print("bottom got", v, "returned", v * 2)
    return v * 2


def middle():
    v = yield from bottom()
    print("middle got", v, "returned", v * 2)
    return v * 2


def top():
    v = yield from middle()
    print("top got", v, "returned", v * 2)
    return v * 2


g = top()
next(g)
# Here we send a value into the bottom generator, the one yielded by middle, which is yielded by top; when bottom generator exhausted (StopIteration raised), v * 2 is returned to middle; middle generator also exhausted here, so (v * 2) * 2 returned to top; top also exhausted, so StopIteration raised with ((v * 2) * 2) * 2
g.send(100)


# This is a generator-based coroutine (it's deprecated)
@asyncio.coroutine
def py34_coro(gen: Iterator):
    yield from gen


g = tp()
cr = py34_coro(g)
next(cr)


# This is a coroutine
async def py35_coro(gen):
    await gen


g = tp()
cr = py34_coro(g)
next(cr)  # Not permitted, 'coroutine' object is not an iterator
