import os
import uuid
import atexit
import asyncio
import inspect
import warnings
from abc import ABC, abstractmethod
from collections import defaultdict
from weakref import ref, WeakMethod
from concurrent.futures import ThreadPoolExecutor

_pool = ThreadPoolExecutor(max_workers=os.cpu_count())

atexit.register(_pool.shutdown)


class EmitterBase(ABC):
    @abstractmethod
    def subscribe(self, event: str, listener): ...
    @abstractmethod
    def unsubscribe(self, event: str, listener): ...
    @abstractmethod
    def emit(self, event, *args, **kwargs): ...
    @abstractmethod
    def clear(self, event: str): ...
    @abstractmethod
    def once(self, event: str, listener): ...


class SyncEmitter(EmitterBase):
    def __init__(self):
        self._listeners = defaultdict(lambda: set())

    def __prepare_listener(self, listener):
        # check if listener is an instance method
        # wrap it in WeakMethod to avoid memory leak
        # else wrap it in ref and return
        if hasattr(listener, "__self__"):
            return WeakMethod(listener)
        return ref(listener)

    def subscribe(self, event: str, listener):
        """
        Subscribe a listener to an event

        Args:
            event (str): Name of the event to subscribe the listener to
            listener (_type_): listener to subscribe to the event
        """
        self._listeners[event].add(self.__prepare_listener(listener))

    def unsubscribe(self, event: str, listener):
        """
        Unsubscribe a listener from an event

        Args:
            event (str): Name of the event to remove the listener from
            listener (_type_): Listener to remove from the event
        """
        if (listeners := self._listeners.get(event)) is not None:
            if not listeners:  # checking if listeners is empty
                self._listeners.pop(event)
                return
            try:
                listeners.remove(self.__prepare_listener(listener))
            except KeyError:
                ...

    def clear(self, event: str):
        """
        Remove all listeners for a given event

        Args:
            event (str): Name of the event to remove all listeners
        """
        self._listeners.pop(event)

    def _call_listener(self, listener, *args, **kwargs):
        listener(*args, **kwargs)

    def once(self, event: str, listener):
        """
        Subscribe a listener to an event that will be called only once

        Args:
            event (str): Name of the event to subscribe the listener to
            listener (_type_): listener to subscribe to the event
        """

        def _listener(*args, **kwargs):
            listener(*args, **kwargs)
            self.unsubscribe(event, _listener)

        self.subscribe(event, _listener)

    def emit(self, event, *args, **kwargs):
        """
        Fire an event and call all listeners subscribed to it

        Args:
            event (_type_): Name of the event to fire
        """
        if listeners := self._listeners.get(event):
            for listener in listeners.copy():
                if obj := listener():
                    self._call_listener(obj, *args, **kwargs)
                else:
                    warnings.warn(f"Listener {listener} is dead, removing it")
                    listeners.remove(listener)


class AsyncEmitter(SyncEmitter):

    def __init__(self, aio: bool = False):
        """
        Emitter class supporting async listeners

        Args:
            aio (bool, optional): If supports passing coroutine functions to the emitted event.
                                  Defaults to False.
        """
        super().__init__()
        self.aio = aio
        self.ident = uuid.uuid4().hex

    @property
    def loop(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        return loop

    @property
    def all_async_tasks(self) -> list[asyncio.Task]:
        """
        All async tasks running in the event loop for all emitter instances

        Returns:
            list[asyncio.Task]: List of all async tasks running in the event loop
        """
        return [
            i
            for i in asyncio.tasks.all_tasks(self.loop)
            if i.get_name().startswith("listener_") and not i.done()
        ]

    @property
    def own_async_tasks(self) -> list[asyncio.Task]:
        """
        List of async tasks running in the event loop for current emitter instance

        Returns:
            list[asyncio.Task]: List of async tasks running in the event loop
        """
        return [
            i for i in self.all_async_tasks if i.get_name().startswith(f"listener_{self.ident}")
        ]

    def _call_listener(self, listener, *args, **kwargs):
        if self.aio:
            is_coro = inspect.iscoroutinefunction(listener)

            # if listener is a coroutine function
            # create a task and run it
            is_coro and self.loop.create_task(
                listener(*args, **kwargs), name=f"listener_{self.ident}_{listener.__name__}"
            )
            # if listener is a normal function
            # run it in executor to avoid blocking the event loop
            not is_coro and self.loop.run_in_executor(_pool, listener, *args, **kwargs)
            return
        # if not aio, run listener in executor
        _pool.submit(listener, *args, **kwargs)


__all__ = ["SyncEmitter", "AsyncEmitter", "EmitterBase"]
