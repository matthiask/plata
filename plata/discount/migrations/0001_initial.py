# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Discount'
        db.create_table('discount_discount', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('type', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('value', self.gf('django.db.models.fields.DecimalField')(max_digits=18, decimal_places=10)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=3, null=True, blank=True)),
            ('tax_class', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['shop.TaxClass'], null=True, blank=True)),
            ('config_json', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('code', self.gf('django.db.models.fields.CharField')(default=u'et4NXLbJoA', unique=True, max_length=30)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('valid_from', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
            ('valid_until', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('allowed_uses', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('used', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('discount', ['Discount'])

        # Adding model 'AppliedDiscount'
        db.create_table('discount_applieddiscount', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('type', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('value', self.gf('django.db.models.fields.DecimalField')(max_digits=18, decimal_places=10)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=3, null=True, blank=True)),
            ('tax_class', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['shop.TaxClass'], null=True, blank=True)),
            ('config_json', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('order', self.gf('django.db.models.fields.related.ForeignKey')(related_name='applied_discounts', to=orm['shop.Order'])),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('remaining', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=18, decimal_places=10)),
        ))
        db.send_create_signal('discount', ['AppliedDiscount'])

    def backwards(self, orm):
        # Deleting model 'Discount'
        db.delete_table('discount_discount')

        # Deleting model 'AppliedDiscount'
        db.delete_table('discount_applieddiscount')

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
        'discount.applieddiscount': {
            'Meta': {'ordering': "['type', 'name']", 'object_name': 'AppliedDiscount'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'config_json': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'applied_discounts'", 'to': "orm['shop.Order']"}),
            'remaining': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '18', 'decimal_places': '10'}),
            'tax_class': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['shop.TaxClass']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'value': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '10'})
        },
        'discount.discount': {
            'Meta': {'object_name': 'Discount'},
            'allowed_uses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'default': "u'Xs6HnukWhg'", 'unique': 'True', 'max_length': '30'}),
            'config_json': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tax_class': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['shop.TaxClass']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'used': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'valid_from': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'valid_until': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '10'})
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
        'shop.taxclass': {
            'Meta': {'ordering': "['-priority']", 'object_name': 'TaxClass'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'priority': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'rate': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'})
        }
    }

    complete_apps = ['discount']