# EventSail

[![codecov](https://codecov.io/gh/satyamsoni2211/eventsail/graph/badge.svg?token=AWAXXSH30S)](https://codecov.io/gh/satyamsoni2211/eventsail) ![PyPI - Implementation](https://img.shields.io/pypi/implementation/eventsail) ![PyPI - Wheel](https://img.shields.io/pypi/wheel/eventsail) ![PyPI - Downloads](https://img.shields.io/pypi/dm/eventsail) ![PyPI - Status](https://img.shields.io/pypi/status/eventsail)

EventSail is a minimal observer pattern package which is performant as well as supports both sync and async operations. Born out of utility and curiosity to replicate Javascript `EventEmitter`, here we are with library with similar functionalities.

![codecov graph](https://codecov.io/gh/satyamsoni2211/eventsail/graphs/sunburst.svg?token=AWAXXSH30S)

## Usage

### Installation

Package can be installed from `PyPi` using below command.

```bash
python -m pip install eventsail
```

If using `poetry` or `pipenv` for packaging, use below command.

```bash
poetry add eventsail
pipenv install eventsail
```

### Info

`EventSail` has a very minimal configuration to get started. It exports `Event` class which consumes `Emitter` under the hood for firing callbacks for the events. For easing, creation of `Event`, `EventSail` also exports `event` method for instantiation.

```python
from eventsail import event, Event
test_event: Event = event('test_event_name')
```

Resultant `test_event` will be a synchronous event type. If you want an asynchronous event, you can instantiate it as.

```python
test_event: Event = event("test", is_sync=False)
```

Now test_event would be of type asynchronous event.

### Subscribing a callback

To register callbacks/handlers, you can either call subscribe method on `Event` instance passing callback/function or you can also use it as decorator over your method.

```python
def foo(*args,**kwargs): ...
test_event.subscribe(foo)
```

or

```python
@test_event.subscribe
def foo(*args,**kwargs): ...
```

> For Async event, all the callbacks will be delegated to threads thus preventing any operations to be blocked.

If you want to leverage power of `async/await` you will have to hint `Event` class to do so by passing `use_asyncio` flag to `True`.

```python
test_event = event("test", is_sync=False, use_asyncio=True)
```

This way it will entertain coroutines as well by creating `Task` and placing them over running event loop. For non coroutine methods, it will execute them over loop in a Thread Pool executor, thus preventing blocking of Event loop.

If you want to call a callback/listener only once, you can use `once` method exposed by `Event` object. Post trigger, listener will be automatically unsubscribed.

```python
@test_event.once
def foo(*args,**kwargs): ...
```

Above callback will only be fired once.

### Unsubscribing a callback

To unsubscribe a callback, you can simply call `unsubscribe` method on Object passing callback you want to unsubscribe.

```python
test_event.unsubscribe(abc)
```

> Calling this method on already unsubscribed callback would do no harm.

To remove all the listeners/callbacks, you can call clear method.

```python
test_event.clear()
```

`Event` class is also singleton class, so you will always get same instance for same set of arguments. This is intentionally kept in place so that we do not loose listeners subscribed.

### Waiting for async tasks

There can be instances where we would need to wait for async emitted tasks to complete before shutdown as this can be critical. `Event` class exposes certain properties containing `async` tasks.

- `Event.all_async_tasks` : This will return all the async tasks scheduled over Event loop for the Emitter.
- `Event.own_async_tasks` : This will only return async tasks corresponding to the immediate parent Emitter of the Event.

To wait for async tasks to complete, `Event` class exposes awaitable API to wait for tasks to complete. This can be called as below.

```python
await test_event.wait_for_async_tasks()
```

This will wait for all the async tasks. This also has a default timeout for 10 seconds post which it will error out.

## Testing

To run tests, simply run below command:

```bash
pytest -s --cov=.
```

## License

`EventSail` is released under the MIT License. See the bundled LICENSE file for details.
