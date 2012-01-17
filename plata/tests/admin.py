from decimal import Decimal

from django.contrib.auth.models import User
from django.forms.models import model_to_dict

import plata
from plata.discount.models import Discount
from plata.shop.models import TaxClass

from plata.tests.base import PlataTest


Product = plata.product_model()


class AdminTest(PlataTest):
    def setUp(self):
        u = User.objects.create_user('admin', 'admin@example.com', 'password')
        u.is_staff = True
        u.is_superuser = True
        u.save()

        product_model = Product
        self.product_admin_url = '/admin/%s/%s/' % (
            product_model._meta.app_label,
            product_model._meta.module_name,
            )

    def login(self):
        self.client.login(username='admin', password='password')

    def test_01_products(self):
        """Test whether the administration interface is well behaved"""
        self.login()

        TaxClass.objects.create(
            name='Standard Swiss Tax Rate',
            rate=Decimal('7.60'),
            )

        product_data = {
            'name': 'Product 3',
            'items_in_stock': 0,

            'prices-0-id': '',
            'prices-0-product': '',

            'prices-0-_unit_price': '79.90',
            'prices-0-currency': 'CHF',
            'prices-0-tax_class': '1',
            'prices-0-tax_included': 'on',

            'prices-INITIAL_FORMS': '0',
            'prices-MAX_NUM_FORMS': '',
            'prices-TOTAL_FORMS': '1',
            }

        self.client.post(self.product_admin_url + 'add/', product_data)
        self.assertEqual(Product.objects.count(), 1)

        self.assertEqual(
            self.client.post(self.product_admin_url + 'add/', product_data).status_code,
            302)

        self.assertEqual(Product.objects.count(), 2)

        p = Product.objects.get(pk=2)

        discount_data = {
            'name': 'Discount 1',
            'type': Discount.PERCENTAGE_VOUCHER,
            'value': 30,
            'code': 'discount1',
            'is_active': True,
            'valid_from': '2010-01-01',
            'valid_until': '',
            'allowed_uses': '',
            'used': 0,
            }

        self.assertContains(self.client.post('/admin/discount/discount/add/', discount_data),
            'required')

        # Does not redirect
        self.assertEqual(self.client.post('/admin/discount/discount/add/', discount_data).status_code, 200)

        discount_data['config_options'] = ('all',)
        self.assertRedirects(self.client.post('/admin/discount/discount/add/', discount_data),
            '/admin/discount/discount/')

        discount_data['config_options'] = ('exclude_sale',)
        discount_data['code'] += '-'
        self.client.post('/admin/discount/discount/add/', discount_data)
        self.assertContains(self.client.get('/admin/discount/discount/2/'),
            'Discount configuration: Exclude sale prices')

        discount_data['name'] = 'Discount 2'
        discount_data['code'] = 'discount2'
        self.assertRedirects(self.client.post('/admin/discount/discount/add/', discount_data),
            '/admin/discount/discount/')

        discount_data = model_to_dict(Discount.objects.get(pk=3))
        discount_data.update({
            'config_options': ('products',),
            'products_products': ('1'),
            'valid_from': '2010-01-01',
            'valid_until': '',
            'allowed_uses': '',
            'used': 0,
            'currency': '',
            'tax_class': '',

            # Manually modified config_json overrides anything selected in the
            # generated form items
            'config_json': u'{"all": {}}',
            })
        self.assertRedirects(self.client.post('/admin/discount/discount/3/', discount_data),
            '/admin/discount/discount/')
