from emitterpy import event, SyncEmitter, AsyncEmitter
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
    print(asyncio.tasks.all_tasks(loop))
    assert len(test_event.emitter.all_async_tasks) == 1
    assert len(test_event.emitter.own_async_tasks) == 1
    await asyncio.gather(*test_event.emitter.all_async_tasks)
    m.assert_called_once()
    assert len(asyncio.tasks.all_tasks(loop)) >= 1
    assert len(test_event.emitter.all_async_tasks) == 0
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
