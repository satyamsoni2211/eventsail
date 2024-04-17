from eventsail import event, SyncEmitter, AsyncEmitter
from unittest.mock import Mock, patch, AsyncMock
import time
import pytest
import asyncio


def test_event_call_delegation():
    test = Mock()
    test_event = event("test")
    with patch.object(test_event, "emitter") as mock:
        test_event.subscribe(test)
        mock.subscribe.assert_called_once()
        test_event.emit()
        mock.emit.assert_called_once()
        test_event.unsubscribe(test)
        mock.unsubscribe.assert_called_once()
        test_event.clear()
        mock.clear.assert_called_once()


def test_sync_event_warning():
    test_event = event("test", is_sync=False)
    test = Mock()
    test_event.subscribe(test)
    with pytest.warns(Warning) as w:
        test_event.own_async_tasks
    assert w[0].message.args[0] == "Event is not async, no async tasks to return"
    assert len(list(test_event.all_async_tasks)) == 0


def test_event_call_once():
    test = Mock()
    test_event = event("test")
    test_event.once(test)
    test_event.emit()
    test.assert_called_once()
    test_event.emit()
    test.assert_called_once()
    test_event.clear()


def test_sync_event():
    test_event = event("test")
    test = Mock()
    test_event.subscribe(test)
    test_event.emit(1, 2, 3)
    test.assert_called_once()
    assert test.call_args == ((1, 2, 3), {})
    test.reset_mock()
    assert len(SyncEmitter()._listeners["test"]) == 1
    test_event.clear()
    assert len(SyncEmitter()._listeners["test"]) == 0


def test_async_event():
    test_event = event("test", is_sync=False)
    test = Mock()
    test_event.subscribe(test)
    test_event.emit(1, 2, 3)
    time.sleep(0.5)
    test.assert_called_once()
    assert test.call_args == ((1, 2, 3), {})
    test.reset_mock()
    assert len(AsyncEmitter()._listeners["test"]) == 1
    test_event.clear()
    assert len(AsyncEmitter()._listeners["test"]) == 0


@pytest.mark.asyncio
async def test_asyncio_event():
    loop = asyncio.get_event_loop()
    test_event = event("test", is_sync=False, use_asyncio=True)
    m = AsyncMock()

    async def test():
        await m()

    test_event.subscribe(test)
    test_event.emit()
    assert len(list(test_event.all_async_tasks)) == 1
    assert len(test_event.own_async_tasks) == 1
    await test_event.wait_for_async_tasks()
    m.assert_called_once()
    assert len(asyncio.tasks.all_tasks(loop)) >= 1
    assert len(list(test_event.all_async_tasks)) == 0
    test_event.clear()


def test_decorator():
    test_event = event("test")
    test = Mock()

    @test_event.subscribe
    def abc():
        test()

    test_event.emit()
    test.assert_called_once()
    assert abc.__name__ == "abc"


def test_event_call_once_decorator():
    test = Mock()

    test_event = event("test")

    @test_event.once
    def abc():
        test()

    test_event.emit()
    test.assert_called_once()
    test_event.emit()
    test.assert_called_once()
    test_event.clear()


def test_event_on():
    test = Mock()
    test2 = Mock()
    event.on("test")(test)
    event.on("test")(test2)
    assert test.event is test2.event
    test.event.emit()
    test.assert_called_once()
    test2.assert_called_once()
    test.event.clear()
    test.event.emit()
    test.assert_called_once()
