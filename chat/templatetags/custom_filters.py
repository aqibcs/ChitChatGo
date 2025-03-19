from django import template

register = template.Library()

@register.filter
def endswith(value, arg):
    """
    Check if the value ends with any of the extensions in arg.
    Args should be comma-separated extensions like '.jpg,.png,.gif'
    """
    if not value:
        return False
    
    extensions = arg.split(',')
    for ext in extensions:
        if value.lower().endswith(ext.lower()):
            return True
    return False
