from django.db import models
from django.utils.translation import gettext as _
from django_countries.fields import CountryField

import plata
from plata.fields import CurrencyField


WEIGHT_UNIT = plata.settings.PLATA_SHIPPING_WEIGHT_UNIT
LENGTH_UNIT = plata.settings.PLATA_SHIPPING_LENGTH_UNIT


class CountryGroup(models.Model):
    """
    A group of countries that are equally expensive with your shopping provider.
    Often this is only one, e.g. your home country or Switzerland.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=63,
        help_text=_('verbose name of this group of countries, e.g. "European Union"'),
    )
    code = models.SlugField(
        verbose_name=_("code"),
        max_length=7,
        help_text=_('short form of the name, e.g. "EU".'),
    )

    class Meta:
        verbose_name = _("country group")
        verbose_name_plural = _("country groups")

    def __str__(self):
        return self.name

    __str__.short_description = _("name")


class Country(models.Model):
    """
    One country where your shipping provider would ship to.
    """

    country = CountryField()
    country_group = models.ForeignKey(
        CountryGroup,
        on_delete=models.CASCADE,
        verbose_name=_("country group"),
        help_text=_(
            "The country belongs to this group of countries for which your"
            " shipping provider charges the same."
        ),
    )

    class Meta:
        verbose_name = _("country")
        verbose_name_plural = _("countries")

    def __str__(self):
        return self.country.name

    __str__.short_description = _("country")

    def name(self):
        return self.country.name


class ShippingProvider(models.Model):
    """
    Postal service
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=63,
        help_text=_('name of the shipping provider, e.g. "Royal Mail".'),
    )
    remarks = models.TextField(
        verbose_name=_("remarks"), help_text=_("internal information"), blank=True
    )
    country_group = models.ManyToManyField(
        CountryGroup,
        verbose_name=_("serves these countries"),
        help_text=_("You can use this service to ship to this group of countries."),
    )

    class Meta:
        verbose_name = _("shipping provider")
        verbose_name_plural = _("shipping providers")

    def __str__(self):
        return self.name

    __str__.short_description = _("name")


class Postage(models.Model):
    """
    One class of shipping postage, e.g. letter or parcel.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=31,
        help_text=_(
            'How your shipping provider calls this class of packet, e.g. "Parcel XL".'
        ),
    )
    provider = models.ForeignKey(
        ShippingProvider, on_delete=models.CASCADE, verbose_name=_("shipping provider")
    )
    country_group = models.ForeignKey(
        CountryGroup,
        on_delete=models.CASCADE,
        verbose_name=_("country group"),
        help_text=_("The tariff is valid for this group of countries."),
    )
    price_internal = models.DecimalField(
        verbose_name=_("internal price"),
        max_digits=10,
        decimal_places=2,
        help_text=_("The price that the provider charges you."),
    )
    price_packaging = models.DecimalField(
        verbose_name=_("packaging price"),
        max_digits=10,
        decimal_places=2,
        # default=plata.settings.PLATA_DEFAULT_PACKAGING_PRICE,
        help_text=_("What the packaging for a packet of this size costs you."),
    )
    price_external = models.DecimalField(
        verbose_name=_("external price"),
        max_digits=10,
        decimal_places=2,
        help_text=_(
            "The price that you charge your customers,"
            " e.g. internal price plus packaging."
        ),
    )
    currency = CurrencyField(
        # verbose_name=_('currency'),
        help_text=_("Currency for all of these prices.")
    )
    price_includes_tax = models.BooleanField(
        verbose_name=_("price includes tax"),
        default=plata.settings.PLATA_PRICE_INCLUDES_TAX,
    )
    weight_packaging = models.PositiveIntegerField(
        verbose_name=_("weight of packaging [%s]" % WEIGHT_UNIT),
        default=0,
        help_text=_("The approx. weight of the necessary packaging for this package"),
    )
    max_weight = models.PositiveIntegerField(
        verbose_name=_("max. weight [%s]" % WEIGHT_UNIT),
        default=0,
        help_text=_("Maximum weight for this tariff. 0 = ignored"),
    )
    max_length = models.PositiveIntegerField(
        verbose_name=_("max. length [%s]" % LENGTH_UNIT),
        default=0,
        help_text=_("Maximum length for this tariff. 0 = ignored"),
    )
    max_width = models.PositiveIntegerField(
        verbose_name=_("max. width [%s]" % LENGTH_UNIT),
        default=0,
        help_text=_("Maximum width for this tariff. 0 = ignored"),
    )
    max_height = models.PositiveIntegerField(
        verbose_name=_("max. height [%s]" % LENGTH_UNIT),
        default=0,
        help_text=_("Maximum height for this tariff. 0 = ignored"),
    )
    max_3d = models.PositiveIntegerField(
        verbose_name=_("max. dimensions [%s]" % LENGTH_UNIT),
        default=0,
        help_text=_(
            "Maximum measure of length+width+height for this tariff. 0 = ignored"
        ),
    )

    class Meta:
        verbose_name = _("postage")
        verbose_name_plural = _("postage classes")

    def __str__(self):
        return f"{self.provider.name}: {self.name}"

    __str__.short_description = _("name")

    def max_weight_f(self):
        """
        maximum weight with unit
        """
        return "%d %s" % (self.max_weight, WEIGHT_UNIT)

    max_weight_f.help_text = _("maximum weight, formatted with unit")
    max_weight_f.short_description = _("max. weight")
    max_weight_f.verbose_name = _("max. weight")

    def max_size(self):
        """
        maximum size of length + width + height, unformatted
        """
        size = 0
        if self.max_length and self.max_width and self.max_height:
            size = self.max_length + self.max_width + self.max_height
            if self.max_3d:
                return min(self.max_3d, size)
        elif self.max_3d:
            size = self.max_3d
        return size

    max_size.help_text = _("maximum size of length + width + height")
    max_size.short_description = _("max. size [%s]" % LENGTH_UNIT)
    max_size.verbose_name = _("max. size [%s]" % LENGTH_UNIT)

    def max_size_f(self):
        """
        maximum size of length + width + height, formatted
        """
        size = 0
        d3 = False
        if self.max_length and self.max_width and self.max_height:
            size = self.max_length + self.max_width + self.max_height
            d3 = True
        if self.max_3d and self.max_3d < size:
            return "%d %s" % (self.max_3d, LENGTH_UNIT)
        if d3:
            return "{} × {} × {} {}".format(
                self.max_length,
                self.max_width,
                self.max_height,
                LENGTH_UNIT,
            )
        return "%d %s" % (size, LENGTH_UNIT)

    max_size_f.help_text = _(
        "maximum size of length + width + height, formatted with unit"
    )
    max_size_f.short_description = _("max. size")
    max_size_f.verbose_name = _("max. size")
