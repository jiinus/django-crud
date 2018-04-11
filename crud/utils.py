# A helper class to easily store choices-values on a class and to get the choice-values
class ValueStore(object):
	@classmethod
	def values(cls):
		return [(y,x) for x, y in cls.__dict__.items() if not x.startswith('__')]

	@classmethod
	def serialize(cls):
		return sorted([{
			'value': value,
			'label': label,
		} for value, label in list(cls.values())], key=lambda k: k['value'])