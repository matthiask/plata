"""
signal handlers to do Google analytics tracking on the server side

to register the handlers you need:

# register ga tracking
from plata.shop import ga_tracking
from plata.shop import signals
signals.order_confirmed.connect(ga_tracking.on_order_confirmed)
signals.order_paid.connect(ga_tracking.on_order_paid)
"""

from django.conf import settings
from django.utils.timezone import now
from pyga.requests import Item, Session, Tracker, Transaction, Visitor


def on_order_confirmed(order, request, **kwargs):
    order.data["google_analytics"] = {
        "utma": request.COOKIES.get("__utma", ""),
        "utmb": request.COOKIES.get("__utmb", ""),
        "meta": {
            "REMOTE_ADDR": request.META.get("REMOTE_ADDR", None),
            "HTTP_USER_AGENT": request.headers.get("user-agent", None),
            "HTTP_ACCEPT_LANGUAGE": request.headers.get("accept-language", None),
        },
    }
    order.save()


def on_order_paid(order, payment, request, **kwargs):
    if not request:
        return

    ga_data = order.data.get("google_analytics", {})
    tracker = Tracker(settings.GOOGLE_ANALYTICS_ID, request.get_host())

    # create visitor
    visitor = Visitor()
    try:
        visitor.extract_from_utma(ga_data.get("utma", ""))
    except ValueError:
        return  # utma cookie value is invalid
    visitor.extract_from_server_meta(ga_data.get("meta", {}))

    # create session
    session = Session()
    try:
        session.extract_from_utmb(ga_data.get("utmb", ""))
    except ValueError:
        return  # utmb cookie value is invalid

    # create transaction
    transaction = Transaction()
    transaction.order_id = order.order_id
    transaction.total = order.subtotal
    transaction.tax = order.tax
    transaction.shipping = order.shipping
    transaction.city = order.billing_city.encode("utf8")
    transaction.country = ("%s" % order.billing_country).encode("utf8")
    transaction.currency = order.currency
    for item in order.items.all():
        i = Item()
        i.sku = item.sku
        i.name = item.name.encode("utf8")
        i.price = item.unit_price
        i.quantity = item.quantity
        transaction.add_item(i)

    # tracker.setcurrencyCode
    tracker.track_transaction(transaction, session, visitor)

    order.data["google_analytics"]["tracked"] = now()
    order.save()
