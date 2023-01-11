
from typing import Dict, List


def get_embedded_key(obj: Dict, keys: List[str]):
	"""Get Object from Dictionary where Key Embedding is a List"""
	for key in keys:
		try:
			obj = obj[key]
		except KeyError:
			return None
	return obj


def get_key(obj: Dict, key: str):
	"""Get Key from Dictionary, embedded or simple"""
	if '.' in key:
		keys = key.split('.')
		return get_embedded_key(obj, keys)
	else:
		return obj.get(key)
