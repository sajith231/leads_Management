from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary using a key.
    Usage: {{ my_dict|get_item:key|default:default_value }}
    """
    if dictionary is None:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def sort_by_latest(cv_list):
    """
    Sort the CV list by ID (or any other field) in descending order.
    """
    try:
        return sorted(cv_list, key=lambda x: x.id, reverse=True)
    except AttributeError:
        return cv_list
