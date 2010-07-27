from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models


class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    raw_id_fields = ('variation',)

class AppliedDiscountInline(admin.TabularInline):
    model = models.AppliedDiscount

class OrderStatusInline(admin.TabularInline):
    model = models.OrderStatus
    extra = 1


class OrderAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    fieldsets = (
        (None, {'fields': ('created', 'confirmed', 'contact', 'email', 'status')}),
        (_('Billing address'), {'fields': ('billing_company', 'billing_first_name',
            'billing_last_name', 'billing_address', 'billing_zip_code',
            'billing_city', 'billing_country')}),
        (_('Shipping address'), {'fields': ('shipping_same_as_billing',
            'shipping_company', 'shipping_first_name',
            'shipping_last_name', 'shipping_address', 'shipping_zip_code',
            'shipping_city', 'shipping_country')}),
        (_('Order items'), {'fields': ('items_subtotal', 'items_discount', 'items_tax')}),
        (_('Shipping'), {'fields': ('shipping_cost', 'shipping_discount', 'shipping_tax')}),
        (_('Total'), {'fields': ('currency', 'total', 'paid')}),
        (_('Additional fields'), {'fields': ('notes',)}),
        )
    inlines = [OrderItemInline, AppliedDiscountInline, OrderStatusInline]
    list_display = ('__unicode__', 'created', 'contact', 'status', 'total',
        'balance_remaining', 'is_paid', 'admin_invoice_pdf', 'admin_packing_slip_pdf')
    list_filter = ('status',)
    raw_id_fields = ('contact',)
    search_fields = tuple('billing_%s' % s for s in models.Order.ADDRESS_FIELDS)\
        +tuple('shipping_%s' % s for s in models.Order.ADDRESS_FIELDS)\
        +('total', 'notes')

    def admin_invoice_pdf(self, instance):
        from django.core.urlresolvers import reverse
        return u'<a href="%(url)s">%(title)s</a>' % {
            'url': reverse('plata_reporting_invoice_pdf',
                args=(),
                kwargs={'order_id': instance.id}
                ),
            'title': _('PDF'),
            }
    admin_invoice_pdf.allow_tags = True
    admin_invoice_pdf.short_description = _('Invoice')

    def admin_packing_slip_pdf(self, instance):
        from django.core.urlresolvers import reverse
        return u'<a href="%(url)s">%(title)s</a>' % {
            'url': reverse('plata_reporting_packing_slip_pdf',
                args=(),
                kwargs={'order_id': instance.id}
                ),
            'title': _('PDF'),
            }
    admin_packing_slip_pdf.allow_tags = True
    admin_packing_slip_pdf.short_description = _('Packing slip')

admin.site.register(models.Order, OrderAdmin)


class OrderPaymentAdmin(admin.ModelAdmin):
    date_hierarchy = 'timestamp'
    list_display = ('order', 'timestamp', 'currency', 'amount', 'status', 'authorized',
        'payment_module', 'payment_method', 'notes_short')
    list_display_links = ('timestamp',)
    list_filter = ('status',)
    raw_id_fields = ('order',)
    search_fields = ('amount', 'payment_module', 'payment_method', 'transaction_id',
        'notes', 'data')

    notes_short = lambda self, obj: (len(obj.notes) > 50) and obj.notes[:40]+'...' or obj.notes
    notes_short.short_description = _('notes')


admin.site.register(models.OrderPayment, OrderPaymentAdmin)
