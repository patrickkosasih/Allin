"""
app_timer.py

The app timer module contains classes that provides an interface to time and schedule functions.

Instead of running a new thread, The scheduling of function calls are done synchronously to the main thread. This is
done by updating the timer groups (the global `default_group` and other local timer groups) every game tick.
"""
import threading
from abc import ABC, abstractmethod
from typing import Callable, Generator, Any


class TimingUtility(ABC):
    """
    The base class for the timer, sequence, and coroutine classes.

    A thing those three classes have in common is the "delay left subtracted by the delta time" system. In the timing
    utility base class, running the `update` method causes the delay left to be subtracted by the current tick's delta
    time; and once the delay left reaches zero, another method, `on_delay_finish` is called. This `on_delay_finish` is
    different for the three different classes.
    """
    def __init__(self, group: None or "TimerGroup"):
        self.group = group if group else default_group

        self.running = True
        self.finished = False
        self.delay_left = 0.0

        self.group.add(self)

    def update(self, dt):
        self.delay_left -= dt

        if self.delay_left <= 0:
            self.on_delay_finish()

    @abstractmethod
    def on_delay_finish(self):
        """
        The method that is run when `delay_left` reaches zero.
        """
        pass


class Timer(TimingUtility):
    """
    The Timer class is used to schedule a function to be called in a set time interval.

    Every tick, the `time_left` attribute of timers are subtracted by the delta time of that tick. Once they reach zero,
    the function is run.
    """

    def __init__(self, delay: float, func: Callable, args=(), group: None or "TimerGroup" = None):
        """
        Params:

        :param delay: How many seconds until the function is called.
        :param func: The function to run.
        :param args: The arguments to pass in the run function.
        :param group: Which timer group to put the timer in. If set to None then the timer would be automatically placed
                      in the global `default_group`, updated in the game's main loop.
        """

        super().__init__(group)

        self.delay_left = delay
        self.func = func
        self.args = args

    def on_delay_finish(self):
        self.func(*self.args)
        self.finished = True


class Sequence(TimingUtility):
    """
    The Sequence class is used to create a sequence of function calls with set delays between them.
    """

    def __init__(self, sequence_list: list[Callable or int or float], group: None or "TimerGroup" = None):
        """
        Params:

        :param sequence_list: A list of functions and numbers (int or float) that make up the sequence of functions and
                              delays to be run. The sequencer iterates through the elements of the sequence list one by
                              one. A number represent the delay between functions in seconds.

        :param group: Which timer group to put the sequence in. If set to None then the timer would be automatically
                      placed in the global `default_group`, updated in the game's main loop.
        """

        for x in sequence_list:
            if not (callable(x) or type(x) is int or type(x) is float):
                raise ValueError(f"invalid item in sequence list (must be either a callable/function or a number): {x}")

        super().__init__(group)

        self.sequence_list = sequence_list
        self.sequence_iter = iter(self.sequence_list)

    def on_delay_finish(self):
        """
        Once the next action delay reaches zero, then the iterator goes to the next item on the list. If the item is a
        function, it is called, and if it's a number, it is added to the next action delay.

        Note that if there are more than one functions in a row in the sequence list, they are run on the same tick.
        """

        while self.delay_left <= 0:
            try:
                action: Callable or int or float
                action = next(self.sequence_iter)
            except StopIteration:
                self.finished = True
                break

            if callable(action):
                action()
            else:
                self.delay_left += action


class Coroutine(TimingUtility):
    """
    The Coroutine class enables adding sleep delays in functions by having a generator function yield how many seconds
    to wait for.
    """

    def __init__(self, target: Generator[int or float or "ThreadWaiter", Any, Any], group: None or "TimerGroup" = None):
        """
        Params:

        :param target: A generator function that will be run by the coroutine. To pause the function, it must yield a
                       number (int or float) that represents how many seconds the function will wait.

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
    # TODO don't be skill issued haiya
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


class TimerGroup:
    """
    Timer groups are used to group instances of the timing utility classes (timers, sequences, and coroutines).
    Timers, sequences, and coroutines can be added, removed, and updated in the timer group altogether, and once they
    are finished running, they are removed from the group.
    """

    def __init__(self):
        self.timers: list[TimingUtility] = []

    def new_timer(self, delay: float, func: Callable, args=()) -> Timer:
        return Timer(delay, func, args, group=self)

    def add(self, timer: TimingUtility) -> None:
        """
        Add a timing utility object (timer/sequence/coroutine) to the timer group. Each timing utility instance can only
        be bound to one anim group, so if the instance is already in another group, then it is removed from its previous
        group.
        """

        if timer.group and timer.group is not self:
            timer.group.remove(timer)

        timer.group = self

        self.timers.append(timer)

    def remove(self, timer: TimingUtility) -> None:
        """
        Remove a timer or sequence from the timer group.
        """
        timer.group = None
        self.timers.remove(timer)

    def update(self, dt: float) -> None:
        """
        Update all the timers and sequences in the timer group.
        """
        for x in self.timers:
            x.update(dt)

            if x.finished:
                self.remove(x)


default_group = TimerGroup()
"""A global timer group that gets updated in the game's main loop. Timing utils that are not assigned to a local timer
group are automatically assigned to this group by default"""
