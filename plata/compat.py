try:
    from django.apps import django_apps
    get_model = django_apps.get_model
except ImportError:
    # Django < 1.7
    from django.db.models import loading
    get_model = loading.get_model
