import csv

from django.http import HttpResponse


def export_as_csv_action(description="Export selected objects as CSV file",
                         header=True):
    """
    This function returns an export csv action
    'header' is whether or not to output the column names as the first row
    TODO: make fields configurable
    """
    def export_as_csv(modeladmin, request, queryset):
        """
        Generic csv export admin action.
        based on http://djangosnippets.org/snippets/1697/
        """
        opts = modeladmin.model._meta

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % \
            unicode(opts).replace('.', '_')

        writer = csv.writer(response, delimiter=';')
        if header:
            writer.writerow(['email', 'firstname', 'lastname', 'status'])
        for o in queryset:
            if o.user is None:
                continue
            writer.writerow([unicode(s).encode("utf-8", "replace") for s in [
                o.user.email, o.user.first_name, o.user.last_name, o.status]])
        return response
    export_as_csv.short_description = description
    return export_as_csv
