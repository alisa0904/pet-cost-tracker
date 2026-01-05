from django import template

register = template.Library()

@register.filter
def divide(value, arg):
    """Безопасное деление для шаблонов"""
    try:
        if value is not None and arg:
            return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        pass
    return 0