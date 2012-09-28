import plata


def plata_context(request):
    """
    Adds a few variables from Plata to the context if they are available:

    * ``plata.shop``: The current :class:`plata.shop.views.Shop` instance
    * ``plata.order``: The current order
    * ``plata.contact``: The current contact instance
    * ``plata.price_includes_tax``: Whether prices include tax or not
    """

    shop = plata.shop_instance()
    return {'plata': {
        'shop': shop,
        'order': shop.order_from_request(request),
        'contact': shop.contact_from_user(request.user),
        'price_includes_tax': plata.settings.PLATA_PRICE_INCLUDES_TAX,
        }} if shop else {}
