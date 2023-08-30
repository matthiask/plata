from django.contrib import admin
from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext_lazy as _
from xlsxdocument import export_selected

from plata.discount.models import AppliedDiscount
from plata.shop import models


class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    raw_id_fields = ("product",)
    extra = 0


class AppliedDiscountInline(admin.TabularInline):
    model = AppliedDiscount
    extra = 0


class OrderStatusInline(admin.TabularInline):
    model = models.OrderStatus
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    date_hierarchy = "created"
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "created",
                    "confirmed",
                    "user",
                    "email",
                    "phone",
                    "language_code",
                    "status",
                )
            },
        ),
        (_("Billing address"), {"fields": models.Order.address_fields("billing_")}),
        (
            _("Shipping address"),
            {
                "fields": (
                    ["shipping_same_as_billing"]
                    + models.Order.address_fields("shipping_")
                )
            },
        ),
        (
            _("Order items"),
            {"fields": ("items_subtotal", "items_discount", "items_tax")},
        ),
        (
            _("Shipping"),
            {"fields": ("shipping_cost", "shipping_discount", "shipping_tax")},
        ),
        (_("Total"), {"fields": ("currency", "total", "paid")}),
        (_("Additional fields"), {"fields": ("notes", "data")}),
    )
    inlines = [OrderItemInline, AppliedDiscountInline, OrderStatusInline]
    list_display = (
        "admin_order_id",
        "created",
        "user",
        "status",
        "total",
        "balance_remaining",
        "admin_is_paid",
        "additional_info",
    )
    list_filter = ("status",)
    ordering = ["-created"]
    raw_id_fields = ("user",)
    readonly_fields = ("status",)
    search_fields = (
        ["_order_id", "email", "total", "notes"]
        + models.Order.address_fields("billing_")
        + models.Order.address_fields("shipping_")
    )

    @admin.display(
        description=_("is paid"),
        boolean=True,
    )
    def admin_is_paid(self, instance):
        return not instance.balance_remaining

    @admin.display(
        description=_("order ID"),
        ordering="_order_id",
    )
    def admin_order_id(self, instance):
        return instance.order_id

    @admin.display(description=_("add. info"))
    def additional_info(self, instance):
        bits = []

        try:
            url = reverse(
                "plata_reporting_packing_slip_pdf", kwargs={"order_id": instance.id}
            )
            bits.append('<a href="{}">{}</a>'.format(url, _("Packing slip")))
        except NoReverseMatch:
            pass

        try:
            url = reverse(
                "plata_reporting_invoice_pdf", kwargs={"order_id": instance.id}
            )
            bits.append('<a href="{}">{}</a>'.format(url, _("Invoice")))
        except NoReverseMatch:
            pass

        return ", ".join(bits)

    actions = [export_selected]


class OrderPaymentAdmin(admin.ModelAdmin):
    date_hierarchy = "timestamp"
    list_display = (
        "order",
        "timestamp",
        "currency",
        "amount",
        "status",
        "authorized",
        "payment_module_key",
        "notes_short",
    )
    list_display_links = ("timestamp",)
    list_filter = ("status", "payment_module_key")
    raw_id_fields = ("order",)
    search_fields = (
        "amount",
        "payment_module",
        "payment_method",
        "transaction_id",
        "notes",
        "data",
    )

    @admin.display(description=_("notes"))
    def notes_short(self, obj):
        return obj.notes[:40] + "..." if len(obj.notes) > 50 else obj.notes


admin.site.register(models.Order, OrderAdmin)
admin.site.register(models.OrderPayment, OrderPaymentAdmin)
admin.site.register(
    models.TaxClass,
    list_display=("name", "rate", "priority"),
    list_editable=("rate", "priority"),
)
