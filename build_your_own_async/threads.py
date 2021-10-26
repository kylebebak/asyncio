"""
https://www.youtube.com/watch?v=Y4Gt3Xjd7G8
https://stackoverflow.com/questions/34469060/python-native-coroutines-and-send
http://www.dabeaz.com/coroutines/
https://snarky.ca/how-the-heck-does-async-await-work-in-python-3-5/
"""

# sequential
import time
import threading


def count_down(n):
    while n > 0:
        print("down", n)
        time.sleep(1)
        n -= 1


def count_up(stop):
    n = 0
    while n < stop:
        print("up", n)
        time.sleep(1)
        n += 1


# count_down(5)
# count_up(5)


# concurrent with threads
threading.Thread(target=count_down, args=(5,)).start()
threading.Thread(target=count_up, args=(5,)).start()
