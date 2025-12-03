# Table of contents

- [Introduction](#introduction)
- [Quickstart](#quickstart)
- [API Overview](#api-overview)
  - [Path parameters](#path-parameters)
  - [Query parameters](#query-parameters)
  - [Body parameters](#body-parameters)
  - [Multi body parameters](#multi-body-parameters)
  - [Query dependency](#query-dependency)
  - [Context dependency](#context-dependency)
- [Testing dependencies](#testing-dependencies)
  - [Overrides](#overrides)
  - [Using requests as test client](#using-requests-as-test-client)
- [Roadmap](#roadmap)
  - [Stuff I'd still like to add](#stuff-id-still-like-to-add)
  - [Requesting features](#requesting-features)

# Introduction

Flastapi is a small flask plugin to enable a Fastapi-like interface to build API endpoints using pydantic.

Current features are:
- path parameters using flask paths
- query parameters
- body parameters using pydantic
- depends (including context dependencies)
- dependency_overrides

Fastapi did a great job at integrating pydantic, as a marshaller for API endpoints, in an intuitive way. With this library I wanted to expose these capabilities in flask as well, for those who haven't found the ability to transition to newer techs (Or those who have a hard time dealing with change ;) )

# Quickstart
```python
from flask import Flask
from flastapi import FlastAPI, Router

app = Flask(__name__)
flastapi = FlastAPI(app)
router = Router("my_router")

@router.get("/index"):
def index():
    return {}

flastapi.add_router(router)

app.run()
```

# API Overview
## Path parameters
Both Flask and Fastapi offer similar path operations. As such, it didn't make sense to build a translation layer from a Fastapi notation to a Flask notation. 

In short: We'll stick to flask path notations :)

### Example endpoint
```python
@router.get("/test/<int:some_param>")
def index(some_param: int):
    return {"some_param": some_param}
```
### Example call
```python
>>> client.get("/test/1")
{"some_param": 1}
```

## Query parameters
Parameters annotated with builtin base types will automatically be flagged as query parameters. It's possible to gather query parameters in a pydantic model, check out the "Query dependency" section for more info.

### Example endpoint
```python
@router.get("/test")
def index(some_param: int):
    return {"some_param": some_param}
```
### Example call
```python
>>> client.get("/test?some_param=1")
{"some_param": 1}
```

## Body parameters
Parameters annotated with pydantic models will automatically be flagged as json typed body parameters.

### Example endpoint
```python
class SomeParam(BaseModel):
    some_int: int


@router.post("/test")
def index(some_param: SomeParam):
    return some_param
```
### Example call
```python
>>> client.post("/test", json={"some_int": 1})
{"some_int": 1}
```

## Multi body parameters
It's possible to annotate multiple pydantic models. If this is the case, the parameter names will be used as a lookup key in the json body.

### Example endpoint
```python
class SomeParam(BaseModel):
    some_int: int


class AnotherParam(BaseModel):
    some_str: str


@router.post("/test")
def index(some_param: SomeParam, another_param: AnotherParam):
    return [SomeParam, AnotherParam]
```
### Example call
```python
>>> client.post("/test", json={
    "some_param": {"some_int": 1},
    "another_param": {"some_str": "blah"}
})
[{"some_int": 1}, {"some_str": "blah"}]
```

## Query dependency
If you'd like to group your query parameters in a pydantic model (or load them through another function), you can use a dependency.

```python
from flastapi import Depends


class SomeParam(BaseModel):
    some_int: int


@router.get("/test")
def index(some_param: SomeParam = Depends(SomeParam)):
    return some_param
```
### Example call
```python
>>> client.get("/test?some_int=1")
{"some_int": 1}
```

## Context dependency
A dependency also supports contexts, if you'd like a context to be started before handling the request, and closed after the request is handled.

```python
from flastapi import Depends


def get_session():
    engine = create_engine("sqlite:////tmp/some.db")
    with Session(engine) as session:
        yield session


@router.get("/test")
def index(session: Session = Depends(get_session)):
    return {}
```

# Testing dependencies
## Overrides
You can override dependencies for your unit tests by replacing the wanted dependency with the one you'd like to run in your tests

### Code
```python
from flastapi import Depends


def get_session():
    engine = create_engine("sqlite:////tmp/some.db")
    with Session(engine) as session:
        yield session


@my_router.get("/test")
def index(session: Session = Depends(get_session)):
    return {}
```

### Tests
```python
from pytest import fixture
from flastapi import FlastAPI

from my_project import get_session, my_router


def get_test_session():
    engine = create_engine("sqlite:////tmp/another.db")
    with Session(engine) as session:
        yield session


@pytest.fixture
def app():
    app = Flask(__name__)
    flastapi = FlastAPI()
    flastapi.add_router(my_router)

    flastapi.dependency_overrides[get_session] = get_test_session
```

## Using requests as test client
If you'd like to use requests as test client, check out [Requests-flask-adapter](https://github.com/maarten-dp/requests-flask-adapter)

# Roadmap
## Stuff I'd still like to add
- Response type
- openAPI/Swagger/ReDoc support
- I need to check out how this whole typing thing works in IDEs (Sorry, I'm a text editor kinda guy)
## Requesting features
If you feel like stuff is missing, feel free to open an issue to request features. I'm but a poor programmer, fiddling for fun in his evenings, so I'll do my best to facilitate.
