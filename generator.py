from itertools import cycle


def endless():
    """Yields 9, 8, 7, 6, 9, 8, 7, 6, ... forever"""
    yield from cycle((9, 8, 7, 6))


def _endless():
    idx = 0
    nums = [9, 8, 7, 6]
    while True:
        yield nums[idx % 4]
        idx += 1


e = _endless()
total = 0
for i in e:
    if total < 100:
        print(i, end=" ")
        total += i
    else:
        print()
        # Pause execution. We can resume later.
        break

# Resume
next(e), next(e), next(e)
