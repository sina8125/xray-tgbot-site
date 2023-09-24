from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ExportActionModelAdmin

from .models import TelegramUser


# Register your models here.


@admin.register(TelegramUser)
class TelegramUserAdmin(ImportExportModelAdmin, ExportActionModelAdmin, admin.ModelAdmin):
    list_display = (
        'id', 'user', 'telegram_id', 'telegram_first_name', 'telegram_last_name', 'telegram_username',
        'telegram_is_staff',
        'banned',)
    readonly_fields = ('last_message_time', 'created_time', 'updated_time',)
    search_fields = ('telegram_id', 'telegram_first_name', 'telegram_last_name', 'telegram_username',)
