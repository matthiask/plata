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


@register.tag
def form_errors(parser, token):
    """
    Show all form and formset errors
    """

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
