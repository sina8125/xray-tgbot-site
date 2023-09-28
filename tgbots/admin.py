from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ExportActionModelAdmin

from .models import TelegramUser
from xraypanels.admin import ClientInLineAdmin


# Register your models here.


@admin.register(TelegramUser)
class TelegramUserAdmin(ImportExportModelAdmin, ExportActionModelAdmin, admin.ModelAdmin):
    inlines = [ClientInLineAdmin]
    list_display = (
        'id', 'user', 'telegram_id', 'telegram_first_name', 'telegram_last_name', 'telegram_username',
        'telegram_is_staff', 'banned', 'last_message_time')
    readonly_fields = ('last_message_time', 'created_time', 'updated_time',)
    search_fields = ('telegram_id', 'telegram_first_name', 'telegram_last_name', 'telegram_username',)
