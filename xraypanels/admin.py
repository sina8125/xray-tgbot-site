from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ExportActionModelAdmin


# Register your models here.

from .models import Client


@admin.register(Client)
class ClientAdmin(ImportExportModelAdmin, ExportActionModelAdmin, admin.ModelAdmin):
    list_display = (
        'id', 'active', 'user', 'telegram_user', 'client_name', 'client_uuid', 'total_flow', 'total_usage',
        'expire_time',)
    search_fields = ('client_name',)
