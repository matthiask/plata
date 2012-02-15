# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TaxClass'
        db.create_table('shop_taxclass', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('rate', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=2)),
            ('priority', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal('shop', ['TaxClass'])

        # Adding model 'Order'
        db.create_table('shop_order', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('billing_company', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('billing_first_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('billing_last_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('billing_address', self.gf('django.db.models.fields.TextField')()),
            ('billing_zip_code', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('billing_city', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('billing_country', self.gf('django.db.models.fields.CharField')(max_length=3, blank=True)),
            ('shipping_same_as_billing', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('shipping_company', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('shipping_first_name', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('shipping_last_name', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('shipping_address', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('shipping_zip_code', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('shipping_city', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('shipping_country', self.gf('django.db.models.fields.CharField')(max_length=3, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('confirmed', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='orders', null=True, to=orm['auth.User'])),
            ('status', self.gf('django.db.models.fields.PositiveIntegerField')(default=10)),
            ('_order_id', self.gf('django.db.models.fields.CharField')(max_length=20, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('items_subtotal', self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=18, decimal_places=10)),
            ('items_discount', self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=18, decimal_places=10)),
            ('items_tax', self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=18, decimal_places=10)),
            ('shipping_method', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('shipping_cost', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=18, decimal_places=10, blank=True)),
            ('shipping_discount', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=18, decimal_places=10, blank=True)),
            ('shipping_tax', self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=18, decimal_places=10)),
            ('total', self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=18, decimal_places=10)),
            ('paid', self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=18, decimal_places=10)),
            ('notes', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('data_json', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('shop', ['Order'])

        # Adding model 'OrderItem'
        db.create_table('shop_orderitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.related.ForeignKey')(related_name='items', to=orm['shop.Order'])),
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['simple.Product'], null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('sku', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('quantity', self.gf('django.db.models.fields.IntegerField')()),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('_unit_price', self.gf('django.db.models.fields.DecimalField')(max_digits=18, decimal_places=10)),
            ('_unit_tax', self.gf('django.db.models.fields.DecimalField')(max_digits=18, decimal_places=10)),
            ('tax_rate', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=2)),
            ('tax_class', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['shop.TaxClass'], null=True, blank=True)),
            ('is_sale', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('_line_item_price', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=18, decimal_places=10)),
            ('_line_item_discount', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=18, decimal_places=10, blank=True)),
            ('_line_item_tax', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=18, decimal_places=10)),
            ('data_json', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('shop', ['OrderItem'])

        # Adding unique constraint on 'OrderItem', fields ['order', 'product']
        db.create_unique('shop_orderitem', ['order_id', 'product_id'])

        # Adding model 'OrderStatus'
        db.create_table('shop_orderstatus', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.related.ForeignKey')(related_name='statuses', to=orm['shop.Order'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('status', self.gf('django.db.models.fields.PositiveIntegerField')(max_length=20)),
            ('notes', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('shop', ['OrderStatus'])

        # Adding model 'OrderPayment'
        db.create_table('shop_orderpayment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.related.ForeignKey')(related_name='payments', to=orm['shop.Order'])),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('status', self.gf('django.db.models.fields.PositiveIntegerField')(default=10)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=2)),
            ('payment_module_key', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('payment_module', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('payment_method', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('transaction_id', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('authorized', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('notes', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('data_json', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('shop', ['OrderPayment'])

    def backwards(self, orm):
        # Removing unique constraint on 'OrderItem', fields ['order', 'product']
        db.delete_unique('shop_orderitem', ['order_id', 'product_id'])

        # Deleting model 'TaxClass'
        db.delete_table('shop_taxclass')

        # Deleting model 'Order'
        db.delete_table('shop_order')

        # Deleting model 'OrderItem'
        db.delete_table('shop_orderitem')

        # Deleting model 'OrderStatus'
        db.delete_table('shop_orderstatus')

        # Deleting model 'OrderPayment'
        db.delete_table('shop_orderpayment')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'shop.order': {
            'Meta': {'object_name': 'Order'},
            '_order_id': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'billing_address': ('django.db.models.fields.TextField', [], {}),
            'billing_city': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'billing_company': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'billing_country': ('django.db.models.fields.CharField', [], {'max_length': '3', 'blank': 'True'}),
            'billing_first_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'billing_last_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'billing_zip_code': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'confirmed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'data_json': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'items_discount': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '18', 'decimal_places': '10'}),
            'items_subtotal': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '18', 'decimal_places': '10'}),
            'items_tax': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '18', 'decimal_places': '10'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'paid': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '18', 'decimal_places': '10'}),
            'shipping_address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'shipping_city': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'shipping_company': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'shipping_cost': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '18', 'decimal_places': '10', 'blank': 'True'}),
            'shipping_country': ('django.db.models.fields.CharField', [], {'max_length': '3', 'blank': 'True'}),
            'shipping_discount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '18', 'decimal_places': '10', 'blank': 'True'}),
            'shipping_first_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'shipping_last_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'shipping_method': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'shipping_same_as_billing': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'shipping_tax': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '18', 'decimal_places': '10'}),
            'shipping_zip_code': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10'}),
            'total': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '18', 'decimal_places': '10'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'orders'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'shop.orderitem': {
            'Meta': {'ordering': "('product',)", 'unique_together': "(('order', 'product'),)", 'object_name': 'OrderItem'},
            '_line_item_discount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '18', 'decimal_places': '10', 'blank': 'True'}),
            '_line_item_price': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '18', 'decimal_places': '10'}),
            '_line_item_tax': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '18', 'decimal_places': '10'}),
            '_unit_price': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '10'}),
            '_unit_tax': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '10'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'data_json': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_sale': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': "orm['shop.Order']"}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['simple.Product']", 'null': 'True', 'blank': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'sku': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'tax_class': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['shop.TaxClass']", 'null': 'True', 'blank': 'True'}),
            'tax_rate': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'})
        },
        'shop.orderpayment': {
            'Meta': {'ordering': "('-timestamp',)", 'object_name': 'OrderPayment'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'authorized': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'data_json': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'payments'", 'to': "orm['shop.Order']"}),
            'payment_method': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'payment_module': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'payment_module_key': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'transaction_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'shop.orderstatus': {
            'Meta': {'ordering': "('created',)", 'object_name': 'OrderStatus'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'statuses'", 'to': "orm['shop.Order']"}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'max_length': '20'})
        },
        'shop.taxclass': {
            'Meta': {'ordering': "['-priority']", 'object_name': 'TaxClass'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'priority': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'rate': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'})
        },
        'simple.product': {
            'Meta': {'ordering': "['ordering', 'name']", 'object_name': 'Product'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ordering': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
        }
    }

    complete_apps = ['shop']