from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _, ugettext


class ContactManager(models.Manager):
    def for_request(self, request, create=False):
        if request.user.is_authenticated():
            try:
                return self.get(user=request.user)
            except self.model.DoesNotExist:
                pass
            except self.model.MultipleObjectsReturned:
                # XXX Oops.
                pass

        if create:
            return Contact.objects.create(
                user=user,
                )


class Contact(models.Model):
    created = models.DateTimeField(_('created'), default=datetime.now)

    user = models.ForeignKey(User, verbose_name=_('user'), related_name='contacts',
        blank=True, null=True)

    first_name = models.CharField(_('first name'), max_length=100)
    last_name = models.CharField(_('last name'), max_length=100)

    manner_of_address = models.CharField(_('Manner of address'), max_length=30,
        blank=True, default='', help_text=_('e.g. Mr., Ms., Dr.'))
    title = models.CharField(_('Title/auxiliary'), max_length=100, blank=True,
        default='', help_text=_('e.g. MSc ETH'))

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = _('contact')
        verbose_name_plural = _('contacts')

    objects = ContactManager()

    def __unicode__(self):
        return u'%s %s' % (self.first_name, self.last_name)


class Address(models.Model):
    contact = models.ForeignKey(Contact, related_name='addresses',
        verbose_name=_('Person'))

    is_billing = models.BooleanField(_('billing'))
    is_shipping = models.BooleanField(_('shipping'))

    email = models.EmailField(_('e-mail address'), blank=True)
    website = models.URLField(verify_exists=False, blank=True)
    function = models.TextField(_('function'), blank=True)
    phone = models.CharField(_('phone'), max_length=30, blank=True,
        help_text=_('Please include the country prefix, but no spaces, e.g. +41555111141'))
    fax = models.CharField(_('fax'), max_length=30, blank=True,
        help_text=_('Please include the country prefix, but no spaces, e.g. +41555111141'))
    mobile = models.CharField(_('mobile'), max_length=30, blank=True,
        help_text=_('Please include the country prefix, but no spaces, e.g. +41555111141'))
    address = models.TextField(_('address'), blank=True)

    zip_code = models.CharField(_('ZIP Code'), max_length=30, blank=True)
    city = models.CharField(_('city'), max_length=30, blank=True)

    region = models.CharField(_('region'), max_length=30, blank=True)
    country = models.CharField(_('country'), max_length=30, blank=True,
        default='CH')

    class Meta:
        verbose_name = _('address')
        verbose_name_plural = _('addresses')

    def __unicode__(self):
        types = []
        if self.is_billing:
            types.append(ugettext('billing'))
        if self.is_shipping:
            types.append(ugettext('shipping'))

        return (types and ugettext(' and ').join(types) + u' ' or u'') + (_('address of %s') % self.contact)
