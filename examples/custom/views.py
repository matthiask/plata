from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views import generic

from custom.models import Contact, Product
from plata.discount.models import Discount
from plata.shop import forms as shop_forms
from plata.shop.models import Order
from plata.shop.views import Shop


class CheckoutForm(shop_forms.BaseCheckoutForm):
    class Meta:
        fields = ["email"] + ["billing_%s" % f for f in Contact.ADDRESS_FIELDS]
        model = Order

    def __init__(self, *args, **kwargs):
        shop = kwargs.get("shop")
        request = kwargs.get("request")
        contact = shop.contact_from_user(request.user)

        if contact:
            initial = {}
            for f in contact.ADDRESS_FIELDS:
                initial["billing_%s" % f] = getattr(contact, f)
                kwargs["initial"] = initial
            initial["email"] = contact.user.email

        super().__init__(*args, **kwargs)

        if not contact:
            self.fields["create_account"] = forms.BooleanField(
                label=_("create account"), required=False, initial=True
            )


class CustomShop(Shop):
    def checkout_form(self, request, order):
        return CheckoutForm


shop = CustomShop(Contact, Order, Discount)


product_list = generic.ListView.as_view(
    queryset=Product.objects.filter(is_active=True),
    template_name="product/product_list.html",
)


class OrderItemForm(forms.Form):
    quantity = forms.IntegerField(
        label=_("quantity"), initial=1, min_value=1, max_value=100
    )


def product_detail(request, object_id):
    product = get_object_or_404(Product.objects.filter(is_active=True), pk=object_id)

    if request.method == "POST":
        form = OrderItemForm(request.POST)

        if form.is_valid():
            order = shop.order_from_request(request, create=True)
            try:
                order.modify_item(product, form.cleaned_data.get("quantity"))
                messages.success(request, _("The cart has been updated."))
            except ValidationError as e:
                if e.code == "order_sealed":
                    [messages.error(request, msg) for msg in e.messages]
                else:
                    raise

            return redirect("plata_shop_cart")
    else:
        form = OrderItemForm()

    return render(
        request, "product/product_detail.html", {"object": product, "form": form}
    )
