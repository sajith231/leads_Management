from django.contrib import admin
from .models import Collection


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display   = ('client_name', 'company', 'department', 'collection_type', 'amount', 'paid_for', 'created_by', 'created_at')
    list_filter    = ('collection_type', 'company')
    search_fields  = ('client_name', 'paid_for', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'created_by')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)