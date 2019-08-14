"""
Template tags for swingtime.
"""

from django import template

from ..views import get_location_list

#####################################################################

register = template.Library()

APP_PREFIX = 'swingtime.'

#####################################################################


@register.filter
def calendar_list(user, perm='book_can_view'):
    """
    {% for cal in user|calendar_list %}
    ...
    {% endfor %}

    {% with calendar_list=user|calendar_list %}
    {% if calendar_list.count > 0 %}
    ...
    {% endif %}
    {% endwith %}

    Optionally allows the permission to list calendars for as well
    (default is view):

    {% ... user|calendar_list:"book_can_edit" %}
    """

    if not perm.startswith(APP_PREFIX):
        perm = APP_PREFIX + perm
    return get_location_list(user, perm)
