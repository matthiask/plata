from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from plata.discount.models import AppliedDiscount
from plata.shop import models


class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    raw_id_fields = ('product',)
    extra = 0

class AppliedDiscountInline(admin.TabularInline):
    model = AppliedDiscount
    extra = 0

class OrderStatusInline(admin.TabularInline):
    model = models.OrderStatus
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    fieldsets = (
        (None, {'fields': ('created', 'confirmed', 'user', 'email', 'status')}),
        (_('Billing address'), {'fields': models.Order.address_fields('billing_')}),
        (_('Shipping address'), {'fields': ['shipping_same_as_billing'] +\
            models.Order.address_fields('shipping_')}),
        (_('Order items'), {'fields': ('items_subtotal', 'items_discount', 'items_tax')}),
        (_('Shipping'), {'fields': ('shipping_cost', 'shipping_discount', 'shipping_tax')}),
        (_('Total'), {'fields': ('currency', 'total', 'paid')}),
        (_('Additional fields'), {'fields': ('notes',)}),
        )
    inlines = [OrderItemInline, AppliedDiscountInline, OrderStatusInline]
    list_display = ('admin_order_id', 'created', 'user', 'status', 'total',
        'balance_remaining', 'is_paid')
    list_filter = ('status',)
    ordering = ['-created']
    raw_id_fields = ('user',)
    search_fields = (['_order_id', 'email', 'total', 'notes'] +
        models.Order.address_fields('billing_') +
        models.Order.address_fields('shipping_'))

    def admin_order_id(self, instance):
        return instance.order_id
    admin_order_id.short_description = _('order ID')
    admin_order_id.admin_order_field = '_order_id'

admin.site.register(models.Order, OrderAdmin)


class OrderPaymentAdmin(admin.ModelAdmin):
    date_hierarchy = 'timestamp'
    list_display = ('order', 'timestamp', 'currency', 'amount', 'status', 'authorized',
        'payment_module_key', 'notes_short')
    list_display_links = ('timestamp',)
    list_filter = ('status', 'payment_module_key')
    raw_id_fields = ('order',)
    search_fields = ('amount', 'payment_module', 'payment_method', 'transaction_id',
        'notes', 'data_json')

    notes_short = lambda self, obj: (len(obj.notes) > 50) and obj.notes[:40]+'...' or obj.notes
    notes_short.short_description = _('notes')

admin.site.register(models.OrderPayment, OrderPaymentAdmin)


admin.site.register(models.TaxClass,
    list_display=('name', 'rate', 'priority'),
    list_editable=('rate', 'priority'),
    )
