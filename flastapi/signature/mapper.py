import inspect

from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError, ErrorWrapper

from .exceptions import ParameterParsing, Missing


class SignatureMapper:
	def __init__(self, func):
		self.func = func
		self.parameters = {}
		self.multi_body = -1
		self.current_fetcher = None

	def __setitem__(self, key, value):
		if isinstance(value, BodyParameter):
			self.multi_body += 1
		self.parameters[key] = value

	def __getitem__(self, key):
		return self.parameters[key]

	def get_kwargs(self, request):
		kwargs = {}
		wrapped_errors = []
		multi_body = self.multi_body
		for name, parameter in self.parameters.items():
			try:
				kwargs[name] = parameter.get_value(request, multi_body)
			except ValidationError as e:
				for error in e.raw_errors:
					error._loc = (name, ) + error.loc_tuple()
				wrapped_errors.extend(e.raw_errors)
			except ValueError as e:
				wrapped_errors.append(ErrorWrapper(e, e.loc))

		if wrapped_errors:
			raise ValidationError(wrapped_errors, BaseModel)

		return kwargs

	def close(self):
		for context in self.contexts:
			context.finalize()


class RequestParameter:
	def __init__(self, name, default, parameter_type):
		self.name = name
		self.default = default
		self.required = default is inspect._empty
		self.parameter_type = parameter_type

	@property
	def loc(self):
		return (self._loc, self.name)

	def get_value(self, request, *args, **kwargs):
		self.validate(request)
		return self._get_value(request, *args, **kwargs)

	def validate(self, request):
		pass


class QueryParameter(RequestParameter):
	_loc = "query"

	def validate(self, request):
		if self.required and self.name not in request.args:
			error = ValueError("field required")
			raise Missing("field required", self.loc)

	def _get_value(self, request, *args, **kwargs):
		value = request.args.get(self.name, inspect._empty)
		if value is inspect._empty:
			return self.default

		try:
			return self.parameter_type(value)
		except Exception as error:
			raise ParameterParsing(str(error), self.loc)


class BodyParameter(RequestParameter):
	_loc = "json"

	def validate(self, request):
		if not request.is_json:
			msg = "Malformed request. Must be application/json"
			raise Missing(msg, self.loc)

	def _get_value(self, request, multi_param, *args, **kwargs):
		body = request.json
		if multi_param:
			body = body.get(self.name)

		if body is None:
			if self.required: 
				raise Missing("field required", self.loc)
			return self.default

		return self.parameter_type(**body)
