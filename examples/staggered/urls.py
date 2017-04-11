import os
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.shortcuts import redirect
from staggered.views import shop


admin.autodiscover()


urlpatterns = [
    url(r'', include(shop.urls)),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^$', lambda request: redirect('plata_product_list'), name='plata_home'),
    url(r'^dashboard/$', lambda request: redirect('/admin/'), name='dashboard'),

    url(r'^products/$', 'staggered.views.product_list',
        name='plata_product_list'),
    url(r'^products/(?P<object_id>\d+)/$', 'staggered.views.product_detail',
        name='plata_product_detail'),

    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': os.path.join(os.path.dirname(__file__), 'media/')}),
]

urlpatterns += staticfiles_urlpatterns()
