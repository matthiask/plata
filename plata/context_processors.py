from example.urls import shop

def plata_context(request):
    return {'plata': {
        'shop': shop,
        'order': shop.order_from_request(request, create=False),
        'contact': shop.contact_from_request(request, create=False),
        }}
