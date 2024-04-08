# EventSail

[![codecov](https://codecov.io/gh/satyamsoni2211/eventsail/graph/badge.svg?token=1LW83DYL0R)](https://codecov.io/gh/satyamsoni2211/eventsail)

EventSail is a minimal observer pattern package which is performant as well as supports both sync and async operations. Born out of utility and curiosity to replicate Javascript `EventEmitter`, here we are with library with similar functionalities.

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

## Testing

To run tests, simply run below command:

```bash
pytest -s --cov=.
```

## License

`EventSail` is released under the MIT License. See the bundled LICENSE file for details.
