import plata


def plata_context(request):
    """
    Adds a few variables from Plata to the context if they are available:

    * ``plata.shop``: The current :class:`plata.shop.views.Shop` instance
    * ``plata.order``: The current order
    * ``plata.contact``: The current contact instance
    """

    shop = plata.shop_instance()
    return {'plata': {
        'shop': shop,
        'order': shop.order_from_request(request),
        'contact': shop.contact_from_user(request.user) if hasattr(request, 'user') else None,
        }} if shop else {}
