from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary using a key.
    Usage: {{ my_dict|get_item:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''




# app1/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def sort_by_latest(cv_list):
    """
    Sort the CV list by ID (or any other field) in descending order.
    """
    return sorted(cv_list, key=lambda x: x.id, reverse=True)