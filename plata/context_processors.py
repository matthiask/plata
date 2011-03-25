import plata

def plata_context(request):
    """
    Adds the current :class:`plata.shop.views.Shop` and (if available)
    the current order and contact instances to the context.
    """

    shop = plata.shop_instance()
    if not shop:
        return {}

    return {'plata': {
        'shop': shop,
        'order': shop.order_from_request(request, create=False),
        'contact': shop.contact_from_user(request.user),
        }}
