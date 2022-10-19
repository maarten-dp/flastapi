import inspect

from flask import current_app, g
from pydantic import BaseModel

from .mapper import (
	SignatureMapper,
	BodyParameter,
	QueryParameter
)

DEPENDENCIES = {}


def parse_signature(func, exclude=None):
	if exclude is None:
		exclude = ()
	signature = inspect.signature(func)
	mapper = SignatureMapper(func)
	for name, parameter in signature.parameters.items():
		if name in exclude:
			continue
		if isinstance(parameter.default, Dependency):
			mapper[name] = parameter.default
		else:
			parameter_type = parameter.annotation
			default = parameter.default
			if issubclass(parameter_type, BaseModel):
				mapper[name] = BodyParameter(name, default, parameter_type)
			else:
				mapper[name] = QueryParameter(name, default, parameter_type)
	return mapper


def Depends(dependency):
	depends = DEPENDENCIES.get(dependency)
	if not depends:
		depends = Dependency(dependency)
		DEPENDENCIES[dependency] = depends
	return depends


class Dependency:
	def __init__(self, dependency):
		self.dependency = dependency
		self.mapper = parse_signature(dependency)
		self.must_close = inspect.isgeneratorfunction(self.dependency)

	def get_value(self, *args, **kwargs):
		dependency = self
		if current_app:
			overrides = current_app.extensions["flastapi"].dependency_overrides
			candidate = overrides.get(self.dependency)
			if candidate:
				dependency = Depends(candidate)
		return dependency._get_value(*args, **kwargs)

	def _get_value(self, request, *args, **kwargs):
		kwargs = self.mapper.get_kwargs(request)
		if self.must_close:
			context = self.dependency(**kwargs)
			if hasattr(g, "contexts"):
				g.contexts.append(context)
			return next(context)
		else:
			return self.dependency(**kwargs)
