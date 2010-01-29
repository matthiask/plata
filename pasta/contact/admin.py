from django.contrib import admin

from pasta.contact import models

class AddressInline(admin.StackedInline):
    model = models.Address
    extra = 1

class ContactAdmin(admin.ModelAdmin):
    inlines = [AddressInline]
    list_display = ('__unicode__', 'company', 'archived', 'person_id', 'contact')
    list_display_links = ('__unicode__',)
    list_editable = ('company', 'archived',)
    list_filter = ('company', 'groups', 'archived', 'contact')
    save_on_top = True
    search_fields = ('sorting_field',)

admin.site.register(models.Contact, ContactAdmin)

admin.site.register(models.Address,
    list_display=('__unicode__', 'address', 'city'),
    search_fields=('contact__name', 'contact__first_name', 'address', 'city'),
    )
