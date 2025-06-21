# app2/templatetags/app2_custom_filters.py

from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter
def highlight_search(text, search_terms):
    """
    Highlights search terms in text with yellow background
    Usage: {{ text|highlight_search:search_terms }}
    """
    if not text or not search_terms:
        return text
    
    text = str(text)
    
    # If search_terms is a string, convert to list
    if isinstance(search_terms, str):
        terms = search_terms.strip().split()
    else:
        terms = search_terms
    
    # Remove empty terms
    terms = [term.strip() for term in terms if term.strip()]
    
    if not terms:
        return text
    
    # Create regex pattern for case-insensitive search
    # Escape special regex characters in search terms
    escaped_terms = [re.escape(term) for term in terms]
    pattern = '|'.join(escaped_terms)
    
    def replace_func(match):
        return f'<mark class="search-highlight">{match.group()}</mark>'
    
    # Perform case-insensitive replacement
    highlighted_text = re.sub(f'({pattern})', replace_func, text, flags=re.IGNORECASE)
    
    return mark_safe(highlighted_text)

@register.filter
def trim(value):
    """Remove leading and trailing whitespace"""
    return value.strip() if isinstance(value, str) else value

@register.filter
def default_if_none_or_empty(value, default):
    """Return default if value is None, empty string, or just whitespace"""
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    return value

@register.filter
def safe_truncate(value, length):
    """Safely truncate text and highlight search terms"""
    if not value:
        return "-"
    value = str(value)
    if len(value) <= length:
        return value
    return value[:length] + "..."