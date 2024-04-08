import asyncio
import pytest
from concurrent.futures import ThreadPoolExecutor
from emitterpy import AsyncEmitter
from unittest.mock import AsyncMock, Mock, patch


def test_async_emitter():
    emitter = AsyncEmitter()
    test = Mock()
    emitter.subscribe("test", test)
    emitter.emit("test")
    test.assert_called_once()
    emitter.unsubscribe("test", test)
    emitter.emit("test")
    test.assert_called_once()
    test.reset_mock()
    emitter.clear("test")


def test_for_singletons():
    emitter = AsyncEmitter()
    emitter2 = AsyncEmitter()
    assert emitter is emitter2


def test_async_emitter_weakref():
    emitter = AsyncEmitter()

    def abc():
        pass

    test = Mock()
    emitter.subscribe("test", test)
    emitter.subscribe("test", abc)
    emitter.emit("test")
    test.assert_called()
    del abc
    emitter.emit("test")
    test.reset_mock()
    emitter.clear("test")


@patch("emitterpy._pool", new_callable=lambda: ThreadPoolExecutor(1))
def test_async_emitter_once(mock_pool):
    emitter = AsyncEmitter()
    test = Mock()
    emitter.once("test", test)
    emitter.emit("test")
    mock_pool.shutdown()
    test.assert_called_once()
    test.reset_mock()
    emitter.clear("test")


@pytest.mark.asyncio
async def test_asyncio_async_emitter():
    loop = asyncio.get_event_loop()
    emitter = AsyncEmitter(aio=True)
    m = AsyncMock()

    async def test():
        await m()

    emitter.subscribe("test", test)
    emitter.emit("test")
    print(asyncio.tasks.all_tasks(loop))
    assert len(emitter.all_async_tasks) == 1
    assert len(emitter.own_async_tasks) == 1
    await asyncio.gather(*emitter.all_async_tasks)
    m.assert_called_once()
    assert len(asyncio.tasks.all_tasks(loop)) >= 1
    await loop.shutdown_asyncgens()
    assert len(emitter.all_async_tasks) == 0
    emitter.clear("test")
