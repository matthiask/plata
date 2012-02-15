from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _


class BaseCheckoutForm(forms.ModelForm):
    """
    Needs self.request
    """

    def __init__(self, *args, **kwargs):
        contact = kwargs.pop('contact')
        shop = kwargs.pop('shop')
        self.request = kwargs.pop('request')

        super(BaseCheckoutForm, self).__init__(*args, **kwargs)

    def clean(self):
        data = super(BaseCheckoutForm, self).clean()

        email = data.get('email')
        create_account = data.get('create_account')

        if email:
            users = list(User.objects.filter(email=email))

            if users:
                if self.request.user not in users:
                    if self.request.user.is_authenticated():
                        self._errors['email'] = self.error_class([
                            _('This e-mail address belongs to a different account.')])
                    else:
                        self._errors['email'] = self.error_class([
                            _('This e-mail address might belong to you, but we cannot know for sure because you are not authenticated yet.')])

        return data


class DiscountForm(forms.Form):
    code = forms.CharField(label=_('code'), max_length=30, required=False)

    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop('order')
        self.discount_model = kwargs.pop('discount_model')
        super(DiscountForm, self).__init__(*args, **kwargs)

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code:
            return self.cleaned_data

        try:
            discount = self.discount_model.objects.get(code=code)
        except self.discount_model.DoesNotExist:
            raise forms.ValidationError(_('This code does not validate'))

        discount.validate(self.order)
        self.cleaned_data['discount'] = discount
        return code


class ConfirmationForm(forms.Form):
    terms_and_conditions = forms.BooleanField(
        label=_('I accept the terms and conditions.'),
        required=True)

    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop('order')
        payment_modules = kwargs.pop('payment_modules')

        super(ConfirmationForm, self).__init__(*args, **kwargs)

        self.fields['payment_method'] = forms.ChoiceField(
            label=_('Payment method'),
            choices=[('', '----------')] + [
                (m.__module__, m.name) for m in payment_modules],
            )

    def clean(self):
        data = super(ConfirmationForm, self).clean()
        self.order.validate(self.order.VALIDATE_ALL)
        return data
