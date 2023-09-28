from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ExportActionModelAdmin

# Register your models here.

from .models import Client, Inbound


@admin.register(Inbound)
class InboundAdmin(ImportExportModelAdmin, ExportActionModelAdmin, admin.ModelAdmin):
    list_display = ('id', 'active', 'inbound_id', 'inbound_name', 'port')
    readonly_fields = ('created_time', 'updated_time')


@admin.register(Client)
class ClientAdmin(ImportExportModelAdmin, ExportActionModelAdmin, admin.ModelAdmin):
    list_display = (
        'id', 'active', 'user', 'telegram_user', 'client_name', 'client_uuid', 'total_flow', 'total_usage', 'price',
        'expire_time', 'created_time', 'updated_time')
    readonly_fields = ('created_time', 'updated_time')
    search_fields = ('client_name', 'telegram_user__telegram_first_name', 'telegram_user__telegram_last_name',
                     'telegram_user__telegram_username', 'telegram_user__telegram_id')


class ClientInLineAdmin(admin.StackedInline):
    model = Client
    fields = ('active', 'client_name', 'client_uuid', 'total_flow', 'total_usage', 'price', 'expire_time')
    extra = 0
