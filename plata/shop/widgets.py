from django.forms.utils import flatatt
from django.forms.widgets import Widget
from django.utils.encoding import force_str
from django.utils.html import format_html


class SubmitButtonInput(Widget):
    input_type = "submit"

    def render(self, name, value, attrs=None):
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        label = final_attrs.pop("label", "None")
        label = force_str(label)
        if value != "":
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs["value"] = value
        return format_html("<button{0} />{1}</button>", flatatt(final_attrs), label)


class PlusMinusButtons(SubmitButtonInput):
    def render(self, name, value, attrs=None):
        button = SubmitButtonInput()
        return "{}{}".format(
            button.render(name, 1, attrs=dict(attrs, label="+")),
            button.render(name, -1, attrs=dict(attrs, label="-")),
        )
