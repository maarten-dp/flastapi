from unittest import mock

import pytest
from flask import Flask
from pydantic import BaseModel

from flastapi import FlastAPI, Router, Depends


@pytest.fixture
def app():
	app = Flask(__name__)
	app.config["PROPAGATE_EXCEPTIONS"] = True
	return app


@pytest.fixture
def flastapi(app):
	return FlastAPI(app)


def test_it_can_register_routes_before_init_app():
	app = Flask(__name__)
	flastapi = FlastAPI()
	router = Router("test_router")

	@router.get("/test")
	def test():
		pass

	flastapi.add_router(router)
	flastapi.init_app(app)

	assert "/test" in [r.rule for r in app.url_map.iter_rules()]


def test_it_can_register_routes_after_init_app():
	app = Flask(__name__)
	flastapi = FlastAPI(app)
	router = Router("test_router")

	@router.get("/test")
	def test():
		pass

	flastapi.add_router(router)

	assert "/test" in [r.rule for r in app.url_map.iter_rules()]


def test_it_can_handle_a_path_request(app, flastapi):
	router = Router("test_router")
	canary = mock.Mock()

	@router.get("/test/<int:some_param>")
	def test(some_param: int):
		canary(some_param)
		return {}

	flastapi.add_router(router)

	with app.app_context():
		with app.test_client() as client:
			client.get("/test/1")

	canary.assert_called_once_with(1)


def test_it_can_handle_a_query_request(app, flastapi):
	router = Router("test_router")
	canary = mock.Mock()

	@router.get("/test")
	def test(some_param: int):
		canary(some_param)
		return {}

	flastapi.add_router(router)

	with app.app_context():
		with app.test_client() as client:
			client.get("/test?some_param=1")

	canary.assert_called_once_with(1)


def test_it_can_handle_a_body_request(app, flastapi):
	router = Router("test_router")
	canary = mock.Mock()

	class SomeParam(BaseModel):
		some_int: int

	@router.get("/test")
	def test(some_param: SomeParam):
		canary(**some_param.dict())
		return {}

	flastapi.add_router(router)

	with app.app_context():
		with app.test_client() as client:
			client.get("/test", json={"some_int": 1})

	canary.assert_called_once_with(some_int=1)


def test_it_can_handle_a_multi_body_request(app, flastapi):
	router = Router("test_router")
	canary = mock.Mock()

	class SomeParam(BaseModel):
		some_int: int

	class AnotherParam(BaseModel):
		some_str: str

	@router.get("/test")
	def test(some_param: SomeParam, another_param: AnotherParam):
		canary(**some_param.dict(), **another_param.dict())
		return {}

	flastapi.add_router(router)

	with app.app_context():
		with app.test_client() as client:
			client.get("/test", json={
				"some_param": {
					"some_int": 1
				},
				"another_param": {
					"some_str": "test"
				}
			})

	canary.assert_called_once_with(some_int=1, some_str="test")


def test_it_can_handle_a_dependency_request(app, flastapi):
	router = Router("test_router")
	canary = mock.Mock()

	def some_dependency():
		return "test"

	@router.get("/test")
	def test(some_param: str = Depends(some_dependency)):
		canary(some_param)
		return {}

	flastapi.add_router(router)

	with app.app_context():
		with app.test_client() as client:
			client.get("/test")

	canary.assert_called_once_with(some_dependency())


def test_it_can_handle_all_request_params(app, flastapi):
	router = Router("test_router")
	canary = mock.Mock()

	class BodyParam(BaseModel):
		some_int: int

	def some_dependency():
		return "test"

	@router.get("/test/<string:path_param>")
	def test(
		path_param: str,
		query_param: int,
		body_param: BodyParam,
		some_dep: str = Depends(some_dependency),
	):
		canary(path_param, query_param, some_dep, **body_param.dict())
		return {}

	flastapi.add_router(router)

	with app.app_context():
		with app.test_client() as client:
			uri = "/test/ayy?query_param=1"
			client.get(uri, json={"some_int": 1})

	canary.assert_called_once_with("ayy", 1, some_dependency(), some_int=1)


# TODO: Fix this =)
# def test_it_can_decorate_multiple_methods(app, flastapi):
# 	router = Router("test_router")
# 	canary = mock.Mock()

# 	@router.get("/test")
# 	@router.post("/test")
# 	def test(method: str):
# 		canary(method)
# 		return {}

# 	flastapi.add_router(router)

# 	with app.app_context():
# 		with app.test_client() as client:
# 			client.get("/test?method=get")
# 			client.post("/test?method=post")

# 	canary.assert_called_once_with("get")
# 	canary.assert_called_once_with("post")


def test_it_can_override_dependencies(app, flastapi):
	router = Router("test_router")
	canary = mock.Mock()

	class BodyParam(BaseModel):
		some_int: int

	def some_dependency():
		return "test"

	def another_dependency():
		return "something entirely different"

	@router.get("/test")
	def test(some_dep: str = Depends(some_dependency)):
		canary(some_dep)
		return {}

	flastapi.add_router(router)
	flastapi.dependency_overrides[some_dependency] = another_dependency

	with app.app_context():
		with app.test_client() as client:
			uri = "/test"
			client.get(uri)

	canary.assert_called_once_with(another_dependency())


def test_it_can_close_a_context_depencency(app, flastapi):
	router = Router("test_router")
	canary = mock.Mock()

	class BodyParam(BaseModel):
		some_int: int

	def context_dependency():
		yield canary
		canary.close()

	@router.get("/test")
	def test(some_dep: str = Depends(context_dependency)):
		canary.close.assert_not_called()
		return {}

	flastapi.add_router(router)

	with app.app_context():
		with app.test_client() as client:
			uri = "/test"
			client.get(uri)

	canary.close.assert_called_once()


def test_it_can_handle_dict_return_value(app, flastapi):
	router = Router("test_router")

	@router.get("/test")
	def test():
		return {"some_int": 1}

	flastapi.add_router(router)

	with app.app_context():
		with app.test_client() as client:
			payload = client.get("/test")

	assert payload.json == {"some_int": 1}


def test_it_can_handle_pydantic_return_value(app, flastapi):
	router = Router("test_router")

	class BodyParam(BaseModel):
		some_int: int

	@router.get("/test")
	def test():
		return BodyParam(some_int=1)

	flastapi.add_router(router)

	with app.app_context():
		with app.test_client() as client:
			payload = client.get("/test")

	assert payload.json == {"some_int": 1}


def test_it_can_handle_nested_pydantic_return_value(app, flastapi):
	router = Router("test_router")

	class BodyParam(BaseModel):
		some_int: int

	@router.get("/test")
	def test():
		return [{"model": BodyParam(some_int=1)}]

	flastapi.add_router(router)

	with app.app_context():
		with app.test_client() as client:
			payload = client.get("/test")

	assert payload.json == [{"model": {"some_int": 1}}]


def test_it_can_handle_a_malformed_requests(app, flastapi):
	router = Router("test_router")

	class BodyParam(BaseModel):
		some_int: int

	@router.get("/test")
	def test(some_param: BodyParam):
		return {}

	flastapi.add_router(router)

	with app.app_context():
		with app.test_client() as client:
			response = payload = client.get("/test")

	assert response.status_code == 400
	assert response.json == [{
		'loc': ['json', 'some_param'],
		'msg': 'Malformed request. Must be application/json',
		'type': 'value_error.missing'
	}]
