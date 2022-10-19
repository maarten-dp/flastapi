from .routing import Router
from .signature import Depends


class FlastAPI:
	def __init__(self, app=None):
		self.app = None
		self.deferred_routers = []
		self.dependency_overrides = {}
		if app:
			self.init_app(app)

	def init_app(self, app):
		self.app = app
		if not hasattr(app, "extensions"):
			app.extensions = {}
		app.extensions["flastapi"] = self
		for router in self.deferred_routers:
			self._add_router(router)

	def add_router(self, router):
		if self.app is None:
			self.deferred_routers.append(router)
		else:
			self._add_router(router)

	def _add_router(self, router):
		self.app.register_blueprint(router.bp)
