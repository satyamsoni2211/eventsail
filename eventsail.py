import os
import uuid
import atexit
import asyncio
import inspect
import warnings
from itertools import chain
from abc import ABC, abstractmethod
from collections import defaultdict
from weakref import ref, WeakMethod
from typing import Optional, Iterable
from concurrent.futures import ThreadPoolExecutor

_pool = ThreadPoolExecutor(max_workers=os.cpu_count())

atexit.register(_pool.shutdown)


class EmitterCore(ABC):

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


class EmitterBase(EmitterCore):

    def __new__(cls, *args, **kwargs):
        # tweaked singleton pattern
        hash_ = cls.get_hash(cls, args, kwargs)
        if not hasattr(cls, "_instances_"):
            setattr(cls, "_instances_", defaultdict(None))
        instance = cls._instances_.get(hash_)
        if not instance:
            cls._instances_[hash_] = instance = super().__new__(cls)
            instance._listeners = defaultdict(set)
            instance
        return instance

    @staticmethod
    def get_hash(cls, args, kwargs):
        return hash((cls, args, frozenset(kwargs.items())))

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


class SyncEmitter(EmitterBase):

    def _call_listener(self, listener, *args, **kwargs):
        listener(*args, **kwargs)


class AsyncEmitter(EmitterBase):

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
                listener(*args, **kwargs), name=f"listener_{self.ident}"
            )
            # if listener is a normal function
            # run it in executor to avoid blocking the event loop
            not is_coro and self.loop.run_in_executor(_pool, listener, *args, **kwargs)
            return
        # if not aio, run listener in executor
        _pool.submit(listener, *args, **kwargs)


class Event(EmitterBase):

    def __init__(self, event: str, is_sync: bool = True, use_asyncio: bool = False):
        self.event = event
        self.is_sync = is_sync
        self.use_asyncio = use_asyncio
        self.emitter = self._populate_emitter()

    def _populate_emitter(self):
        """
        Populate the emitter based on the event type
        """
        cls = SyncEmitter if self.is_sync else AsyncEmitter
        args = {}
        if not self.is_sync and self.use_asyncio:
            args["aio"] = self.use_asyncio
        return cls(**args)

    def subscribe(self, listener):
        """
        Subscribe a listener to an event

        Args:
            listener (_type_): listener to subscribe to the event
        """
        self.emitter.subscribe(self.event, listener)
        return listener

    def unsubscribe(self, listener):
        """
        Unsubscribe a listener from an event

        Args:
            listener (_type_): Listener to remove from the event
        """
        self.emitter.unsubscribe(self.event, listener)

    def emit(self, *args, **kwargs):
        """
        Fire an event and call all listeners subscribed to it
        """
        self.emitter.emit(self.event, *args, **kwargs)

    def clear(self):
        """
        Remove all listeners for a given event

        Args:
            event (str): Name of the event to remove all listeners
        """
        self.emitter.clear(self.event)

    def once(self, listener):
        """
        Subscribe a listener to an event that will be called only once

        Args:
            listener (_type_): listener to subscribe to the event
        """
        self.emitter.once(self.event, listener)
        return listener

    @property
    def all_async_tasks(self) -> Optional[Iterable[asyncio.Task]]:
        """
        All async tasks running in the event loop for all emitter instances

        Returns:
            list[asyncio.Task]: List of all async tasks running in the event loop
        """
        return chain.from_iterable(
            [i.own_async_tasks for i in AsyncEmitter()._instances_.values() if i.aio]
        )

    @property
    def own_async_tasks(self) -> Optional[list[asyncio.Task]]:
        """
        List of async tasks running in the event loop for current emitter instance

        Returns:
            list[asyncio.Task]: List of async tasks running in the event loop
        """
        if self.is_sync or (not self.is_sync and not self.use_asyncio):
            warnings.warn("Event is not async, no async tasks to return")
            return
        hash_ = self.get_hash(self.emitter.__class__, (), {"aio": self.use_asyncio})
        return self.emitter._instances_[hash_].own_async_tasks

    async def wait_for_async_tasks(self):
        """
        Wait for all async tasks to complete
        """
        await asyncio.wait(self.all_async_tasks, timeout=10)


def event(event: str, is_sync: bool = True, use_asyncio: bool = False) -> Event:
    """
    Factory function to create an event

    Args:
        event (str): Name of the event
        is_sync (bool, optional): If Event is synchronous. Defaults to True.
        use_asyncio (bool, optional): If Event supports coroutine execution.
                                    Defaults to False.

    Returns:
        Event: Instance of Event class
    """
    return Event(event, is_sync, use_asyncio)


def on(event: str, is_sync: bool = True, use_asyncio: bool = False):
    """
    Decorator to subscribe a function to an event. Returns listener instance with event bound to
    the listener instance. Can be accessed using `listener.event`.

    Args:
        event (str): Name of the event
        is_sync (bool, optional): If Event is synchronous. Defaults to True.
        use_asyncio (bool, optional): If Event supports coroutine execution.
                                    Defaults to False.
    """

    def _on(listener):
        event_ = Event(event, is_sync, use_asyncio)
        event_.subscribe(listener)
        listener.event = event_
        return listener

    return _on


event.on = on

__all__ = ["SyncEmitter", "AsyncEmitter", "EmitterBase"]
