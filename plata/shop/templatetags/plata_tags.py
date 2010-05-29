from django import forms, template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = template.Library()


@register.inclusion_tag('_form_item.html')
def form_item(item, additional_classes=None):
    """
    Helper for easy displaying of form items.
    """

    return {
        'item': item,
        'additional_classes': additional_classes,
        }


@register.inclusion_tag('_form_item_plain.html')
def form_item_plain(item):
    """
    Helper for easy displaying of form items.
    """

    return {
        'item': item,
        }


@register.inclusion_tag('_form_item_ac.html')
def form_item_ac(item, selected):
    return {
        'item': item,
        'selected': selected,
        }


@register.tag
def form_errors(parser, token):
    tokens = token.split_contents()

    return FormErrorsNode(*tokens[1:])


class FormErrorsNode(template.Node):
    def __init__(self, *items):
        self.items = [template.Variable(item) for item in items]

    def render(self, context):
        items = []
        for item in self.items:
            try:
                var = item.resolve(context)
                if isinstance(var, dict):
                    items.extend(var.values())
                elif isinstance(var, (list, tuple)):
                    items.extend(var)
                else:
                    items.append(var)
            except template.VariableDoesNotExist:
                # We do not care too much
                pass

        errors = False

        form_list = []
        formset_list = []

        for i in items:
            if isinstance(i, forms.BaseForm):
                form_list.append(i)
            else:
                formset_list.append(i)

            if getattr(i, 'errors', None) or getattr(i, 'non_field_errors', lambda:None)():
                errors = True

        if not errors:
            return u''

        return render_to_string('_form_errors.html', {
            'forms': form_list,
            'formsets': formset_list,
            'errors': True,
            })


@register.filter
def has(obj, var):
    return var in obj


@register.filter(name='getattr')
def _getattr(obj, name):
    try:
        return obj[name]
    except (TypeError, KeyError):
        try:
            return getattr(obj, name)
        except (TypeError, AttributeError):
            return None

"""
@register.filter
def currency(value):
    return mark_safe(_currency(value, thousands_separator='&lsquo;'))
"""
