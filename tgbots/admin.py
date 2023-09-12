from django.contrib import admin

from .models import TelegramUser


# Register your models here.


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'telegram_id', 'is_now_admin')
    readonly_fields = ('last_message_time','created_time', 'updated_time',)
