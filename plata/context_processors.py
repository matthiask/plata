import plata
from plata.product.models import Category

def plata_context(request):
    shop = plata.shop_instance()

    return {'plata': {
        'shop': shop,
        'order': shop.order_from_request(request, create=False),
        'contact': shop.contact_from_request(request, create=False),
        'categories' : Category.objects.public(),
        }}

