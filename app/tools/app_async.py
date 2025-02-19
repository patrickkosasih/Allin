import threading
import time

from app.tools.app_timer import TimingUtility, TimerGroup
from app.shared import *


class Coroutine(TimingUtility):
    """
    The Coroutine class enables pausing functions by having a generator function that yields a number or a ThreadWaiter
    object.

    For the generator function to pause, it must yield a number (int or float) that represents how many seconds the
    function will wait. Another way is to yield a ThreadWaiter object, where the coroutine will wait until the task of
    the ThreadWaiter is complete.
    """

    def __init__(self, target: Generator[int or float or "ThreadWaiter", Any, Any], group: None or "TimerGroup" = None):
        """
        Params:

        :param target: A generator function that will be run by the coroutine.

        :param group: Which timer group to put the coroutine in. If set to None then the timer would be automatically
                      placed in the global `default_group`, updated in the game's main loop.
        """
        super().__init__(group)

        self.thread_waiter: ThreadWaiter or None = None
        self.generator_iter = iter(target)

        self.ret_value = None

    def on_delay_finish(self):
        if self.thread_waiter and not self.thread_waiter.finished:
            return

        try:
            ret = next(self.generator_iter)
        except StopIteration as e:
            self.finished = True
            self.ret_value = e.value
            return

        if not ret:
            pass
        elif type(ret) is int or type(ret) is float:
            self.delay_left += ret
        elif type(ret) is ThreadWaiter:
            self.thread_waiter = ret
        else:
            raise TypeError(f"invalid yield return value from the coroutine's generator: {ret}")


class ThreadWaiter:
    """
    The ThreadWaiter class is used to call a function from a coroutine and run it on a new thread. When the coroutine
    yields the ThreadWaiter object, the coroutine waits until the thread is finished executing. The return value of the
    threaded function can then be retreived from the `task_result` property.
    """
    def __init__(self, task: Callable, args=(), auto_start=True):
        self._finished = False

        self.task = task
        self._args = args

        self._task_thread = threading.Thread(target=self._thread_run)
        self._task_result = None

        if auto_start:
            self.start()

    def start(self):
        self._task_thread.start()

    def _thread_run(self):
        self._task_result = self.task(*self._args)
        self._finished = True

    @property
    def task_result(self):
        return self._task_result

    @property
    def finished(self):
        return self._finished


func_coroutine_running: dict[Callable, bool] = {}


def run_as_coroutine(func: Callable[Any, Generator]):
    """
    A decorator that turns a generator function into a regular function that automatically creates a coroutine object
    for the original generator.
    """
    def wrapper(*args, **kwargs):
        Coroutine(func(*args, **kwargs))

    return wrapper


def run_as_serial_coroutine(func: Callable[Any, Generator]):
    """
    Similar to `run_as_coroutine` but there can only be a maximum of one coroutine running the function at the same time.
    """
    def limited_func(*args, **kwargs):
        if func_coroutine_running.setdefault(func, False):
            return

        try:
            func_coroutine_running[func] = True
            yield from func(*args, **kwargs)
        finally:
            func_coroutine_running[func] = False

    return run_as_coroutine(limited_func)


def app_await(coroutine: Coroutine):
    # idfk what is this
    while not coroutine.finished:
        yield 0

    return coroutine.ret_value
