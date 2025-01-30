from django import template

register = template.Library()

@register.filter
def chunkify(value, chunk_size):
    """Splits the input list into chunks of the specified size."""
    if value is None:
        return []
    return [value[i:i + chunk_size] for i in range(0, len(value), chunk_size)]
