from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.forms.formsets import all_valid
from django.forms.models import modelform_factory, inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _

from pasta.product.models import Product


class Contact(models.Model):
    user = models.ForeignKey(User, verbose_name=_('user'), blank=True, null=True)
    email = models.EmailField(_('e-mail address'), unique=True)
    created = models.DateTimeField(_('created'), default=datetime.now)

    billing_company = models.CharField(_('company'), max_length=100, blank=True)
    billing_first_name = models.CharField(_('first name'), max_length=100, blank=True)
    billing_last_name = models.CharField(_('last name'), max_length=100, blank=True)
    billing_address = models.TextField(_('address'), blank=True)
    billing_zip_code = models.CharField(_('ZIP code'), max_length=50, blank=True)
    billing_city = models.CharField(_('city'), max_length=100, blank=True)
    billing_country = models.CharField(_('country'), max_length=2, blank=True,
        help_text=_('ISO2 code'))

    shipping_same_as_billing = models.BooleanField(_('shipping address equals billing address'),
        default=True)

    shipping_company = models.CharField(_('company'), max_length=100, blank=True)
    shipping_first_name = models.CharField(_('first name'), max_length=100, blank=True)
    shipping_last_name = models.CharField(_('last name'), max_length=100, blank=True)
    shipping_address = models.TextField(_('address'), blank=True)
    shipping_zip_code = models.CharField(_('ZIP code'), max_length=50, blank=True)
    shipping_city = models.CharField(_('city'), max_length=100, blank=True)
    shipping_country = models.CharField(_('country'), max_length=2, blank=True,
        help_text=_('ISO2 code'))

    currency = models.CharField(_('currency'), max_length=10)

    class Meta:
        verbose_name = _('contact')
        verbose_name_plural = _('contacts')

    def __unicode__(self):
        return u'%s %s' % (self.billing_first_name, self.billing_last_name)


class Order(models.Model):
    CART = 'cart'
    CHECKOUT = 'checkout'
    CONFIRMED = 'confirmed'
    COMPLETED = 'completed'

    STATUS_CHOICES = (
        (CART, _('is a cart')),
        (CHECKOUT, _('checkout process started')),
        (CONFIRMED, _('order has been confirmed')),
        (COMPLETED, _('order has been completed')),
        )

    ADDRESS_FIELDS = ['company', 'first_name', 'last_name', 'address',
        'zip_code', 'city', 'country']

    created = models.DateTimeField(_('created'), default=datetime.now)
    modified = models.DateTimeField(_('modified'), default=datetime.now)
    contact = models.ForeignKey(Contact, verbose_name=_('contact'))

    #order_id = models.CharField(_('order ID'), max_length=20, unique=True)

    billing_company = models.CharField(_('company'), max_length=100, blank=True)
    billing_first_name = models.CharField(_('first name'), max_length=100, blank=True)
    billing_last_name = models.CharField(_('last name'), max_length=100, blank=True)
    billing_address = models.TextField(_('address'), blank=True)
    billing_zip_code = models.CharField(_('ZIP code'), max_length=50, blank=True)
    billing_city = models.CharField(_('city'), max_length=100, blank=True)
    billing_country = models.CharField(_('country'), max_length=2, blank=True,
        help_text=_('ISO2 code'))

    shipping_company = models.CharField(_('company'), max_length=100, blank=True)
    shipping_first_name = models.CharField(_('first name'), max_length=100, blank=True)
    shipping_last_name = models.CharField(_('last name'), max_length=100, blank=True)
    shipping_address = models.TextField(_('address'), blank=True)
    shipping_zip_code = models.CharField(_('ZIP code'), max_length=50, blank=True)
    shipping_city = models.CharField(_('city'), max_length=100, blank=True)
    shipping_country = models.CharField(_('country'), max_length=2, blank=True,
        help_text=_('ISO2 code'))

    currency = models.CharField(_('currency'), max_length=10)
    subtotal = models.DecimalField(_('subtotal'), max_digits=10,
        decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(_('discount'), max_digits=10,
        decimal_places=2, default=Decimal('0.00'))
    tax = models.DecimalField(_('Tax'), max_digits=10, decimal_places=2,
        default=Decimal('0.00'),
        help_text=_('Set tax rate to 0.0 to create an invoice without a tax line.'))
    total = models.DecimalField(_('total'), max_digits=10, decimal_places=2,
        default=Decimal('0.00'))

    paid = models.DecimalField(_('paid'), max_digits=10, decimal_places=2,
        default=Decimal('0.00'),
        help_text=_('This much has been paid already.'))

    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES,
        default=CART, db_index=True)
    notes = models.TextField(_('notes'), blank=True)

    class Meta:
        verbose_name = _('contact')
        verbose_name_plural = _('contacts')

    def __unicode__(self):
        return u'Order #%d' % self.pk

    @property
    def balance_remaining(self):
        return (self.total - self.paid).quantize(Decimal('0.00'))

    @property
    def is_paid(self):
        return self.balance_remaining <= 0


class OrderItem(models.Model):
    order = models.ForeignKey(Order)
    product = models.ForeignKey(Product)

    quantity = models.IntegerField(_('amount'))

    unit_price = models.DecimalField(_('unit price'), max_digits=18, decimal_places=10)
    unit_tax = models.DecimalField(_('unit tax'), max_digits=18, decimal_places=10)

    line_item_price = models.DecimalField(_('line item price'), max_digits=18, decimal_places=10)
    line_item_tax = models.DecimalField(_('line item tax'), max_digits=18, decimal_places=10)

    discount = models.DecimalField(_('discount'), max_digits=18, decimal_places=10)

    class Meta:
        verbose_name = _('order item')
        verbose_name_plural = _('order items')


class OrderStatus(models.Model):
    order = models.ForeignKey(Order)
    created = models.DateTimeField(_('created'), default=datetime.now)
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES)
    notes = models.TextField(_('notes'), blank=True)

    class Meta:
        get_latest_by = 'created'
        ordering = ('created',)
        verbose_name = _('order status')
        verbose_name_plural = _('order statuses')

    def save(self, *args, **kwargs):
        super(OrderStatus, self).save(*args, **kwargs)
        self.order.status = self.status
        self.order.modified = self.created
        self.order.save()


class OrderPayment(models.Model):
    order = models.ForeignKey(Order)
    created = models.DateTimeField(_('created'), default=datetime.now)

    amount = models.DecimalField(_('amount'), max_digits=10, decimal_places=2)

    def _recalculate_paid(self):
        paid = OrderPayment.objects.filter(order=self.order_id).aggregate(
            total=Sum('amount'))['total'] or 0

        Order.objects.filter(id=self.order_id).update(paid=paid)

    def save(self, *args, **kwargs):
        super(OrderPayment, self).save(*args, **kwargs)
        self._recalculate_paid()

    def delete(self, *args, **kwargs):
        super(OrderPayment, self).delete(*args, **kwargs)
        self._recalculate_paid()



class Shop(object):
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        return patterns('',
            url(r'^cart/$', self.cart, name='pasta_shop_cart'),
            url(r'^checkout/$', self.checkout, name='pasta_shop_checkout'),
            url(r'^confirmation/$', self.confirmation, name='pasta_shop_confirmation'),
            )

    @property
    def urls(self):
        return self.get_urls()


    def get_product_model(self):
        if not hasattr(self, '_product_model'):
            self._product_model = type('Product', (ProductBase,), {})
        return self._product_model

    def get_order_model(self):
        if not hasattr(self, '_order_model'):
            self._order_model = type('Order', (OrderBase,), {})
        return self._order_model

    def get_orderitem_model(self):
        return self.order_model.items.related.model

    @property
    def product_model(self):
        return self.get_product_model()

    @property
    def order_model(self):
        return self.get_order_model()

    def order_from_request(self, request, create=False):
        try:
            return self.order_model.objects.get(pk=request.session.get('shop_order'))
        except (ValueError, self.order_model.DoesNotExist):
            if create:
                order = self.order_model.objects.create()
                request.session['shop_order'] = order.pk
                return order

        return None

    def contact_from_request(self, request, create=False):
        # TODO: check whether user is logged in, reuse information
        try:
            return self.contact_model.objects.get(pk=request.session.get('shop_contact'))
        except (ValueError, self.contact_model.DoesNotExist):
            if create:
                contact = self.contact_model.objects.create()
                request.session['shop_contact'] = contact.pk
                return contact

        return None


    def get_context(self, request, context):
        instance = RequestContext(request, self.get_extra_context(request))
        instance.update(context)
        return instance


    def cart(self, request):
        order = self.order_from_request(request, create=False)

        OrderItemFormset = inlineformset_factory(
            self.order_model,
            self.get_orderitem_model(),
            extra=0)

        if request.method == 'POST':
            formset = OrderItemFormset(request.POST, instance=order)

            if formset.is_valid():
                formset.save()

                messages.success(request, _('The cart has been updated.'))

                return HttpResponseRedirect('.')
        else:
            formset = OrderItemFormset(instance=order)

        return self.render_cart(request, {
            'order': order,
            'orderitemformset': formset,
            'empty': request.GET.get('empty', False), # Whether the cart is empty.
                                                      # Flag gets set by checkout view.
            })

    def render_cart(self, request, context):
        return render_to_response('pasta/shop_cart.html',
            self.get_context(request, context))

    def checkout(self, request):
        order = self.order_from_request(request, create=False)

        if not order:
            return HttpResponseRedirect(reverse('pasta_shop_cart') + '?empty=1')

        OrderForm = modelform_factory(self.order_model)

        if request.method == 'POST':
            form = OrderForm(request.POST, instance=order)

            if form.is_valid():
                form.save()

                return redirect('pasta_shop_confirmation')
        else:
            form = OrderForm(instance=order)

        return render_checkout(request, {
            'order': order,
            'orderform': form,
            })

    def render_checkout(self, request, context):
        return render_to_response('pasta/shop_checkout.html',
            self.get_context(request, context))


class OrderProcessor(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def apply(self, order, items, state, **kwargs):
        pass

        # Processing has completed
        return True


class PriceProcessor(OrderProcessor):
    def apply(self, order, items, state, **kwargs):
        for item in items:
            item.price = item.quantity * item.product.unit_price
        return True


class TaxProcessor(OrderProcessor):
    pass

class ShippingProcessor(OrderProcessor):
    pass

class AutomaticDiscount(OrderProcessor):
    def apply(self, order, items, state, **kwargs):
        for item in items:
            if not hasattr(item, 'discount'):
                item.discount = Decimal('1.00')
                item.price -= item.discount
        return True

class PercentageDiscount(OrderProcessor):
    pass

class AmountDiscount(OrderProcessor):
    pass




class OldOrder(models.Model):
    processor_classes = {}

    created = models.DateTimeField(_('created'), default=datetime.now)

    @classmethod
    def register_processor(cls, sequence_nr, processor):
        cls.processor_classes['%02d_%s' % (sequence_nr, processor.__name__)] =\
            processor

    @classmethod
    def remove_processor(cls, processor):
        for k, v in cls.processor_classes.iteritems():
            if v == processor:
                del cls.processor_classes[k]

    def recalculate_items(self, items, **kwargs):
        state = {
            'pass': 0,
            }

        processors = dict((k, v()) for k, v in self.processor_classes.iteritems())
        keys = sorted(processors.keys())

        while keys:
            state['pass'] += 1

            toremove = [key for key in keys if \
                processors[key].apply(self, items, state, **kwargs) != False]
            keys = [key for key in keys if key not in toremove]

            if state['pass'] > 10:
                raise Exception('Too many passes while recalculating order total.')

        print state


OldOrder.register_processor(10, PriceProcessor)
OldOrder.register_processor(20, PercentageDiscount)
OldOrder.register_processor(21, AutomaticDiscount)
OldOrder.register_processor(30, TaxProcessor)
OldOrder.register_processor(40, ShippingProcessor)
OldOrder.register_processor(50, AmountDiscount)



class OrderItem(models.Model):
    order = models.ForeignKey(Order)
    product = models.ForeignKey(Product)

    quantity = models.IntegerField(_('amount'))

    """
    unit_price = models.DecimalField(_('unit price'), max_digits=18, decimal_places=10)
    unit_tax = models.DecimalField(_('unit tax'), max_digits=18, decimal_places=10)

    line_item_price = models.DecimalField(_('line item price'), max_digits=18, decimal_places=10)
    line_item_tax = models.DecimalField(_('line item tax'), max_digits=18, decimal_places=10)

    discount = models.DecimalField(_('discount'), max_digits=18, decimal_places=10)
    """





class PriceProcessor(object):
    def product_price(self, product):
        pass

    def line_item_price(self, line_item):
        pass

