from django import template

register = template.Library()


@register.inclusion_tag('html/modal_fade.html')
def render_modal(modal_id, title, content, buttons):
    return {
        'modal_id': modal_id,
        'title': title,
        'content': content,
        'buttons': buttons,
    }
