class ParameterParsing(ValueError):
	code = "parsing"
	def __init__(self, message, loc):
		self.message = message
		self.loc = loc

	def __str__(self):
		return self.message

	def __repr__(self):
		return self.message


class Missing(ParameterParsing):
	code = "missing"
