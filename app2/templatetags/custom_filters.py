from django import template

register = template.Library()

@register.filter
def trim(value):
    return value.strip() if isinstance(value, str) else value