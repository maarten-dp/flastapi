from functools import partialmethod, wraps

from flask import Blueprint, request, jsonify, g
from werkzeug.routing import Rule, Map
from pydantic import BaseModel

from .signature import parse_signature


def extract_path_parameters(raw_rule):
	rule = Rule(raw_rule)
	rule.bind(Map())
	return list(rule._converters.keys())


def close_open_contexts():
	if hasattr(g, "contexts"):
		for context in g.contexts:
			try:
				next(context)
			except StopIteration:
				pass


def to_dict(payload):
	if isinstance(payload, dict):
		for name, value in payload.items():
			payload[name] = to_dict(value)
	if isinstance(payload, (set, tuple, list)):
		payload = [to_dict(p) for p in payload]
	if isinstance(payload, BaseModel):
		payload = payload.dict()
	return payload


def make_request_handler(view_func, path_parameters):
	signature_mapper = parse_signature(view_func, exclude=path_parameters)
	def handle_request(*args, **kwargs):
		g.contexts = []
		kwargs.update(signature_mapper.get_kwargs(request))
		# TODO: handle return type
		return_value = view_func(*args, **kwargs)
		close_open_contexts()
		return jsonify(to_dict(return_value))
	return handle_request


class Router:
	def __init__(self, name):
		self.endpoints = []
		self.bp = Blueprint(name, __name__)

	def _dispatch(self, path, *args, **kwargs):
		def endpoint_wrapper(view_func):
			path_parameters = extract_path_parameters(path)
			request_handler = make_request_handler(view_func, path_parameters)
			self.bp.route(path, *args, **kwargs)(request_handler)
			return wraps(view_func)(request_handler)
		return endpoint_wrapper

	get = partialmethod(_dispatch, methods=["GET"])
	post = partialmethod(_dispatch, methods=["POST"])
	put = partialmethod(_dispatch, methods=["PUT"])
	patch = partialmethod(_dispatch, methods=["PATCH"])
	delete = partialmethod(_dispatch, methods=["DELETE"])
