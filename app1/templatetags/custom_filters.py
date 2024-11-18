from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary using a key
    Usage: {{ my_dict|get_item:key }}
    """
    if dictionary is None:
        return ''
    return dictionary.get(str(key), '')