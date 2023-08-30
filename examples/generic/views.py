from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views import generic

from generic.models import Product
from plata.contact.models import Contact
from plata.discount.models import Discount
from plata.shop.models import Order
from plata.shop.views import Shop


shop = Shop(Contact, Order, Discount)


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
                order.modify_item(product, relative=form.cleaned_data.get("quantity"))
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
