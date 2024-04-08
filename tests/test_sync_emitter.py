import re
import pytest
from unittest.mock import Mock
from emitterpy import SyncEmitter


def test_sync_emitter():
    emitter = SyncEmitter()
    test = Mock()
    emitter.subscribe("test", test)
    emitter.emit("test")
    test.assert_called_once()
    emitter.unsubscribe("test", test)
    emitter.emit("test")
    test.assert_called_once()
    test.reset_mock()


def test_sync_emitter_multiple_calls():
    emitter = SyncEmitter()
    test = Mock()
    emitter.subscribe("test", test)
    emitter.subscribe("test", test)
    emitter.emit("test")
    test.assert_called_once()
    emitter.unsubscribe("test", test)
    emitter.unsubscribe("test", test)
    test.reset_mock()


def test_sync_emitter_weakref():
    with pytest.warns(Warning) as w:
        emitter = SyncEmitter()

        def abc():
            pass

        test = Mock()
        emitter.subscribe("test", test)
        emitter.subscribe("test", abc)
        emitter.emit("test")
        test.assert_called()
        del abc
        emitter.emit("test")
        emitter.unsubscribe("test", test)
        test.reset_mock()
    msg = w.list[0].message.args[0]
    assert re.match("Listener <weakref at .* is dead", msg)


def test_sync_emitter_once():
    emitter = SyncEmitter()
    test = Mock()
    emitter.once("test", test)
    emitter.emit("test")
    test.assert_called_once()
    emitter.emit("test")
    test.assert_called_once()
    test.reset_mock()


def test_sync_emitter_clear():
    emitter = SyncEmitter()
    test = Mock()
    emitter.subscribe("test", test)
    emitter.clear("test")
    assert emitter._listeners.get("test") is None
    emitter.emit("test")
    test.assert_not_called()
    test.reset_mock()


def test_unsubscribed_listeners():
    emitter = SyncEmitter()

    def abc():
        pass

    test = Mock()
    emitter.subscribe("test", test)
    emitter.subscribe("test", abc)
    emitter.emit("test")
    emitter.unsubscribe("test", abc)
    emitter.unsubscribe("test", abc)
    assert len(emitter._listeners["test"]) == 1


def test_class_method():
    class A(object):
        def __init__(self) -> None:
            self.called = False

        def foo(self):
            self.called = True

    a = A()
    emitter = SyncEmitter()
    emitter.subscribe("test", a.foo)
    emitter.emit("test")
    assert a.called
