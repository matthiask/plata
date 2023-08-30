from django import forms
from django.contrib import auth
from django.utils.translation import gettext_lazy as _

from plata.shop import signals
from plata.shop.widgets import PlusMinusButtons, SubmitButtonInput


try:  # pragma: no cover
    from django.contrib.auth import get_user_model

    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User


class BaseCheckoutForm(forms.ModelForm):
    """
    Needs the request and the shop object as keyword argument
    """

    def __init__(self, *args, **kwargs):
        self.shop = kwargs.pop("shop")
        self.request = kwargs.pop("request")

        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()

        if data.get("email"):
            users = list(User.objects.filter(email=data.get("email")))

            if users and self.request.user not in users:
                if self.shop.user_is_authenticated(self.request.user):
                    self._errors["email"] = self.error_class(
                        [_("This e-mail address belongs to a different account.")]
                    )
                else:
                    self._errors["email"] = self.error_class(
                        [
                            _(
                                "This e-mail address might belong to you, but"
                                " we cannot know for sure because you are"
                                " not authenticated yet."
                            )
                        ]
                    )

        return data

    def save(self):
        """
        Save the order, create or update the contact information
        (if available) and return the saved order instance
        """
        order = super().save(commit=False)
        contact = self.shop.contact_from_user(self.request.user)

        if contact:
            order.user = contact.user
        elif self.shop.user_is_authenticated(self.request.user):
            order.user = self.request.user

        if (self.cleaned_data.get("create_account") and not contact) or (
            not contact and self.shop.user_is_authenticated(self.request.user)
        ):
            password = None
            email = self.cleaned_data.get("email")

            if not self.shop.user_is_authenticated(self.request.user):
                password = User.objects.make_random_password()
                params = {"email": email, "password": password}
                if getattr(User, "USERNAME_FIELD", "username") == "username":
                    params["username"] = email[:30]  # FIXME
                user = User.objects.create_user(**params)
                user = auth.authenticate(username=email, password=password)
                auth.login(self.request, user)
            else:
                user = self.request.user

            contact = self.shop.contact_model(user=user)
            order.user = user

            signals.contact_created.send(
                sender=self.shop,
                user=user,
                contact=contact,
                password=password,
                request=self.request,
            )

        order.save()

        if contact:
            contact.update_from_order(order, request=self.request)
            contact.save()

        return order


class DiscountForm(forms.Form):
    code = forms.CharField(label=_("code"), max_length=30, required=False)

    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop("order")
        self.discount_model = kwargs.pop("discount_model")
        request = kwargs.pop("request")  # noqa
        shop = kwargs.pop("shop")  # noqa

        super().__init__(*args, **kwargs)

    def clean_code(self):
        code = self.cleaned_data.get("code")
        if not code:
            return self.cleaned_data

        try:
            discount = self.discount_model.objects.get(code=code)
        except self.discount_model.DoesNotExist:
            raise forms.ValidationError(_("This code does not validate"))

        discount.validate(self.order)
        self.cleaned_data["discount"] = discount
        return code

    def save(self):
        """
        Save the discount (or do nothing if no discount code has been given)
        """
        if "discount" in self.cleaned_data:
            self.cleaned_data["discount"].add_to(self.order)


class ConfirmationForm(forms.Form):
    terms_and_conditions = forms.BooleanField(
        label=_("I accept the terms and conditions."), required=True
    )

    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop("order")
        self.request = kwargs.pop("request")
        self.shop = kwargs.pop("shop")
        self.payment_modules = self.shop.get_payment_modules(self.request)

        super().__init__(*args, **kwargs)

        method_choices = [(m.key, m.name) for m in self.payment_modules]
        if len(method_choices) > 1:
            method_choices.insert(0, ("", "---------"))
        self.fields["payment_method"] = forms.ChoiceField(
            label=_("Payment method"), choices=method_choices
        )

    def clean(self):
        data = super().clean()
        self.order.validate(self.order.VALIDATE_ALL)
        return data

    def process_confirmation(self):
        """
        Process the successful order submission
        """
        self.order.update_status(self.order.CONFIRMED, "Confirmation given")
        signals.order_confirmed.send(
            sender=self.shop, order=self.order, request=self.request
        )

        module = {m.key: m for m in self.payment_modules}[
            self.cleaned_data["payment_method"]
        ]

        return module.process_order_confirmed(self.request, self.order)


class OrderItemForm(forms.Form):
    """
    Used in single page checkout cart
    """

    relative = forms.IntegerField(widget=PlusMinusButtons(), required=False)
    absolute = forms.IntegerField(
        widget=SubmitButtonInput(attrs={"label": _("Remove")}), required=False
    )

    def __init__(self, *args, **kwargs):
        self.orderitem = kwargs.pop("orderitem")
        kwargs["prefix"] = "{}_{}".format(
            kwargs.get("prefix", "orderitem"),
            self.orderitem.id,
        )
        initial = kwargs.pop("initial", {})
        initial["absolute"] = 0
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)

    def clean(self):
        if (self.cleaned_data["absolute"] is None) == (
            self.cleaned_data["relative"] is None
        ):
            raise forms.ValidationError(_('Provide either "relative" or "absolute".'))
        if self.cleaned_data["absolute"] is None:
            del self.cleaned_data["absolute"]
        if self.cleaned_data["relative"] is None:
            del self.cleaned_data["relative"]
        return self.cleaned_data

    def save(self):
        if len(self.cleaned_data) == 1:  # either absolute or relative is set
            order = self.orderitem.order
            order.modify_item(self.orderitem.product, **self.cleaned_data)


class PaymentSelectMixin:
    """
    Handles the payment selection field
    """

    def get_payment_field(self, shop, request):
        self.payment_modules = shop.get_payment_modules(request)
        method_choices = [(m.key, m.name) for m in self.payment_modules]
        if len(method_choices) > 1:
            method_choices.insert(0, ("", "---------"))
        return forms.ChoiceField(label=_("Payment method"), choices=method_choices)

    def payment_order_confirmed(self, order, payment_method):
        module = {m.key: m for m in self.payment_modules}[payment_method]
        return module.process_order_confirmed(self.request, order)


class PaymentSelectForm(forms.Form, PaymentSelectMixin):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        self.shop = kwargs.pop("shop")
        super().__init__(*args, **kwargs)
        self.fields["payment_method"] = self.get_payment_field(self.shop, self.request)


class SinglePageCheckoutForm(BaseCheckoutForm, PaymentSelectMixin):
    """
    Handles shipping and billing addresses,
    payment method and terms and conditions
    """

    terms_and_conditions = forms.BooleanField(
        label=_("I accept the terms and conditions."), required=True
    )

    class Meta:
        exclude = ("shipping_country", "billing_country")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["payment_method"] = self.get_payment_field(self.shop, self.request)

        self.REQUIRED_ADDRESS_FIELDS = [
            name[9:] for name in self.fields if name.startswith("shipping_")
        ]
        self.REQUIRED_ADDRESS_FIELDS.remove("company")

    def clean(self):
        data = super().clean()
        if not data.get("shipping_same_as_billing"):
            for f in self.REQUIRED_ADDRESS_FIELDS:
                field = "shipping_%s" % f
                if not data.get(field):
                    self._errors[field] = self.error_class(
                        [_("This field is required.")]
                    )
        self.instance.validate(self.instance.VALIDATE_ALL)
        return data

    def save(self):
        """
        Process the successful order submission
        """
        self.instance.update_status(self.instance.CONFIRMED, "Confirmation given")
        signals.order_confirmed.send(
            sender=self.shop, order=self.instance, request=self.request
        )

        return self.payment_order_confirmed(
            self.instance, self.cleaned_data["payment_method"]
        )
