from typing import Any, Dict, List, Optional, Tuple, Union


def get_embedded_value(obj: Dict, keys: List):
    """Get Object from Dictionary where Key Embedding is a List"""
    for key in keys:
        try:
            obj = obj[key]
        except KeyError:
            return None
    return obj


def get_value(obj: Union[Dict, object], key: str):
    """Get Value from Object, Dictionary, embedded or simple"""

    # Get Value by Key if Dictionary
    if isinstance(obj, Dict):
        if '.' in key:
            keys = key.split('.')
            return get_embedded_value(obj, keys)
        else:
            return obj.get(key)

    # Else Get Value by Attribute if Object
    return getattr(obj, key, None)


def equal(a: Any, b: Any) -> bool:
    return a == b


def not_equal(a: Any, b: Any) -> bool:
    return a != b


def gt(a: Any, b: Any) -> bool:
    return a > b


def lt(a: Any, b: Any) -> bool:
    return a < b


def gte(a: Any, b: Any) -> bool:
    return a >= b


def lte(a: Any, b: Any) -> bool:
    return a <= b


def contains(a: Any, b: Any) -> bool:
    return a in b


def not_contains(a: Any, b: Any) -> bool:
    return a not in b


operator_map = {
    None: equal,
    "not": not_equal,
    "gt": gt,
    "lt": lt,
    "gte": gte,
    "lte": lte,
    "in": contains,
    "not_in": not_contains
}


def get_operator(filter_key: Optional[str] = None) -> Tuple[str, callable]:
    """Get Operator"""
    if filter_key is None:
        return filter_key, operator_map[None]

    split_filter_key = filter_key.split("__")

    assert len(split_filter_key) in (
        1, 2,), "Strings can only contain single operator"

    if len(split_filter_key) == 1:
        return filter_key, operator_map[None]

    filter_key, operator_key = split_filter_key

    assert operator_key in operator_map, f"`{operator_key}` not valid operator"

    return filter_key, operator_map[operator_key]


def apply_filter(obj: Union[Any, Dict], filter_value: Any, filter_key: Optional[str] = None):
    """Apply Filter to an Object"""
    filter_key, operator = get_operator(filter_key)

    # Get Value
    if filter_key is None:
        value = obj
    else:
        value = get_value(obj, filter_key)

    return operator(value, filter_value)


def apply_filters(obj: Union[Any, Dict], filters: Optional[Dict] = None):
    """Apply Filters to Object Payload"""
    # No Need to Filter if no filters applied
    if filters is None:
        return True

    # Apply Filters
    return all(
        apply_filter(obj=obj, filter_value=filter_value, filter_key=filter_key)
        for filter_key, filter_value in filters.items()
    )
