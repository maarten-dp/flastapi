from unittest import mock

import pytest
from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError
from flastapi.signature import (
	parse_signature, QueryParameter, BodyParameter, Depends, Dependency
)


class SomeParam(BaseModel):
	some_int: int
	some_str: str

class AnotherParam(BaseModel):
	some_int: int
	some_str: str


def test_it_can_assess_query_request_parameters():
	def func(some_int: int, some_str: str):
		pass

	signature_mapper = parse_signature(func)
	assert isinstance(signature_mapper["some_int"], QueryParameter)
	assert isinstance(signature_mapper["some_str"], QueryParameter)


def test_it_can_assess_a_body_request_parameter():
	def func(some_param: SomeParam):
		pass

	signature_mapper = parse_signature(func)
	assert not signature_mapper.multi_body
	assert isinstance(signature_mapper["some_param"], BodyParameter)


def test_it_can_assess_multiple_body_request_parameters():
	def func(some_param: SomeParam, another_param: AnotherParam):
		pass

	signature_mapper = parse_signature(func)
	assert signature_mapper.multi_body
	assert isinstance(signature_mapper["some_param"], BodyParameter)
	assert isinstance(signature_mapper["another_param"], BodyParameter)


def test_it_can_assess_query_and_body_parameters():
	def func(some_int: int, some_param: SomeParam):
		pass

	signature_mapper = parse_signature(func)
	assert isinstance(signature_mapper["some_int"], QueryParameter)
	assert isinstance(signature_mapper["some_param"], BodyParameter)


def test_it_can_assess_query_and_mulit_body_parameters():
	def func(some_int: int, some_param: SomeParam, another_param: AnotherParam):
		pass

	signature_mapper = parse_signature(func)
	assert signature_mapper.multi_body
	assert isinstance(signature_mapper["some_int"], QueryParameter)
	assert isinstance(signature_mapper["some_param"], BodyParameter)
	assert isinstance(signature_mapper["another_param"], BodyParameter)


def test_it_can_assess_a_query_dependency_parameter():
	def func(some_param: SomeParam = Depends(SomeParam)):
		pass

	signature_mapper = parse_signature(func)
	assert isinstance(signature_mapper["some_param"], Dependency)
	dependency_mapper = signature_mapper["some_param"].mapper
	assert isinstance(dependency_mapper["some_int"], QueryParameter)
	assert isinstance(dependency_mapper["some_str"], QueryParameter)


def test_it_can_get_correct_kwargs_from_query():
	request = mock.Mock(args={
		"some_int": "10",
		"some_str": "test"
	})

	def func(some_int: int, some_str: str):
		pass

	signature_mapper = parse_signature(func)
	kwargs = signature_mapper.get_kwargs(request)
	assert kwargs == {
		"some_int": 10,
		"some_str": "test"
	}


def test_it_can_get_correct_default_kwargs_from_query():
	request = mock.Mock(args={})

	def func(some_int: int = 10, some_str: str = "test"):
		pass

	signature_mapper = parse_signature(func)
	kwargs = signature_mapper.get_kwargs(request)
	assert kwargs == {
		"some_int": 10,
		"some_str": "test"
	}


def test_it_can_get_correct_single_body_kwargs():
	request = mock.Mock(json={
		"some_int": "10",
		"some_str": "test"
	})

	def func(some_param: SomeParam):
		pass

	signature_mapper = parse_signature(func)
	kwargs = signature_mapper.get_kwargs(request)
	assert kwargs == {
		"some_param": SomeParam(**{
			"some_int": 10,
			"some_str": "test"
		})
	}


def test_it_can_get_correct_multi_body_kwargs():
	request = mock.Mock(json={
		"some_param": {
			"some_int": "10",
			"some_str": "test"
		},
		"another_param":{
			"some_int": "20",
			"some_str": "blah"
		}
	})

	def func(some_param: SomeParam, another_param: AnotherParam):
		pass

	signature_mapper = parse_signature(func)
	kwargs = signature_mapper.get_kwargs(request)
	assert kwargs == {
		"some_param": SomeParam(**{
			"some_int": 10,
			"some_str": "test"
		}),
		"another_param": AnotherParam(**{
			"some_int": 20,
			"some_str": "blah"
		})
	}


def test_it_can_get_correct_query_and_body_kwargs():
	request = mock.Mock(
		args={
			"some_int": "10"
		},
		json={
			"some_int": "20",
			"some_str": "test"
		}
	)
	def func(some_int: int, some_param: SomeParam):
		pass

	signature_mapper = parse_signature(func)
	kwargs = signature_mapper.get_kwargs(request)
	assert kwargs == {
		"some_int": 10,
		"some_param": SomeParam(**{
			"some_int": 20,
			"some_str": "test"
		}),
	}


def test_it_can_get_correct_dependency_kwargs_from_query():
	request = mock.Mock(args={
		"some_int": "10",
		"some_str": "test"
	})

	def func(some_param: SomeParam = Depends(SomeParam)):
		pass

	signature_mapper = parse_signature(func)
	kwargs = signature_mapper.get_kwargs(request)
	assert kwargs == {
		"some_param": SomeParam(**{
			"some_int": 10,
			"some_str": "test"
		})
	}


def test_it_can_get_correct_child_dependency_kwargs():
	request = mock.Mock(args={
		"some_int": "10",
		"some_str": "test"
	})

	class SomeChildParam(SomeParam):
		dep: int = Depends(lambda: 1)

	def func(some_param: SomeChildParam = Depends(SomeChildParam)):
		pass

	signature_mapper = parse_signature(func)
	kwargs = signature_mapper.get_kwargs(request)
	assert kwargs == {
		"some_param": SomeChildParam(**{
			"some_int": 10,
			"some_str": "test",
			"dep": 1,
		})
	}


def test_it_can_detect_missing_query_parameter():
	request = mock.Mock(args={})

	def func(some_int: int):
		pass

	signature_mapper = parse_signature(func)
	with pytest.raises(ValidationError) as exc:
		signature_mapper.get_kwargs(request)
	
	assert exc.value.errors() == [{
		'ctx': {
			'loc': ('query', 'some_int'),
			'message': 'field required'
		},
		'loc': ('query', 'some_int'),
		'msg': 'field required',
		'type': 'value_error.missing'
	}]


def test_it_can_handle_wrong_query_type_value():
	request = mock.Mock(args={"some_int": "test"})

	def func(some_int: int):
		pass

	signature_mapper = parse_signature(func)
	with pytest.raises(ValidationError) as exc:
		signature_mapper.get_kwargs(request)

	assert exc.value.errors() == [{
		'ctx': {
			'loc': ('query', 'some_int'),
			'message': "invalid literal for int() with base 10: 'test'"
		},
		'loc': ('query', 'some_int'),
		'msg': "invalid literal for int() with base 10: 'test'",
		'type': 'value_error.parsing'
	}]


def test_it_can_handle_not_json_request():
	request = mock.Mock(is_json=False)

	def func(some_param: SomeParam):
		pass

	signature_mapper = parse_signature(func)
	with pytest.raises(ValidationError) as exc:
		signature_mapper.get_kwargs(request)

	assert exc.value.errors() == [{
		'ctx': {
			'loc': ('json', 'some_param'),
          	'message': 'Malformed request. Must be application/json'
        },
		'loc': ('json', 'some_param'),
		'msg': 'Malformed request. Must be application/json',
		'type': 'value_error.missing'
  	}]


def test_it_can_handle_missing_json_request():
	request = mock.Mock(is_json=True, json={})

	def func(some_param: SomeParam):
		pass

	signature_mapper = parse_signature(func)
	with pytest.raises(ValidationError) as exc:
		signature_mapper.get_kwargs(request)

	assert exc.value.errors() == [
		{
			'loc': ('some_param', 'some_int'),
			'msg': 'field required',
			'type': 'value_error.missing'
		}, {
			'loc': ('some_param', 'some_str',),
			'msg': 'field required',
			'type': 'value_error.missing'
		}
	]


def test_it_can_ignore_path_parameters():
	def func(path_param:str, some_int: int):
		pass

	signature_mapper = parse_signature(func, exclude=["path_param"])
	assert list(signature_mapper.parameters.keys()) == ["some_int"]
