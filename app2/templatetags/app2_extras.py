from django import template

register = template.Library()

@register.filter
def split(value, sep=','):
    """Split a string by the given separator."""
    return value.split(sep)

@register.filter
def trim(value):
    """Strip leading / trailing spaces safely, even if value is not string."""
    return str(value).strip()

@register.filter
def get_item(dictionary, key):
    """Return dictionary[key] or 0"""
    return (dictionary or {}).get(key, 0)