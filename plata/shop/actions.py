import csv

from django.http import HttpResponse

from plata.shop.models import Order, OrderItem
from simple_shop.models import Product
from symposion.speakers.models import Speaker

def export_as_csv_action(description="Export selected objects as CSV file",
                         header=True):
    """
    This function returns an export csv action
    'header' is whether or not to output the column names as the first row
    """
    def export_as_csv(modeladmin, request, queryset):
        """
        Generic csv export admin action.
        based on http://djangosnippets.org/snippets/1697/
        """
        opts = modeladmin.model._meta

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % unicode(opts).replace('.', '_')

        CO = Product.objects.filter(name__contains=u'Conference Track')
        TU_A = Product.objects.filter(name__contains=u'Advanced Tutorials')
        TU_B = Product.objects.filter(name__contains=u'Beginner Tutorials')

        writer = csv.writer(response, delimiter=';')
        if header:
            writer.writerow(['email', 'firstname', 'lastname', 'affiliation', 'conference', 'tutorials_adv', 'tutorials_beg', 'status'])
        for o in queryset:
            if o.user is None:
                continue
            co_n = 0
            tu_a_n = 0
            tu_b_n = 0
            for i in o.items.all():
                if i.product in CO:
                    co_n += i.quantity
                elif i.product in TU_A:
                    tu_a_n += i.quantity
                elif i.product in TU_B:
                    tu_b_n += i.quantity
            try:
                affiliation = Speaker.objects.get(user=o.user).affiliation
            except:
                affiliation = ''
            writer.writerow([unicode(s).encode("utf-8", "replace") for s in [o.user.email, o.user.first_name, o.user.last_name, affiliation, co_n, tu_a_n, tu_b_n, o.status]])
        return response
    export_as_csv.short_description = description
    return export_as_csv
