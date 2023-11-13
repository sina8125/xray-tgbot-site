from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.utils import timezone


# Create your models here.

class TelegramUser(models.Model):
    user = models.OneToOneField(User, related_name='client_user', null=True, blank=True, on_delete=models.SET_NULL)
    inviting_user = models.ForeignKey('self', null=True, blank=True, on_delete=models.DO_NOTHING)
    telegram_first_name = models.CharField(max_length=150, null=True, blank=True)
    telegram_last_name = models.CharField(max_length=150, null=True, blank=True)
    telegram_id = models.BigIntegerField(unique=True, null=False, blank=False)
    telegram_username = models.CharField(max_length=32, validators=[MinLengthValidator(5)], null=True, blank=True)
    wallet_balance = models.PositiveIntegerField(null=True, blank=True)
    telegram_is_staff = models.BooleanField(default=False, null=False, blank=True)
    is_now_admin = models.BooleanField(default=False, null=False, blank=True)
    banned = models.BooleanField(default=False, null=False, blank=True)
    last_message_time = models.DateTimeField(auto_now=True)
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'telegram_users'
        verbose_name = 'Telegram User'
        verbose_name_plural = 'Telegram Users'

    def __str__(self):
        return self.get_telegram_full_name() or self.telegram_username or str(self.telegram_id)

    def clean(self):
        if self.banned and self.telegram_is_staff:
            raise ValidationError('admin cannot be banned!!!')
        if self.is_now_admin and not self.telegram_is_staff:
            raise ValidationError('Only staff users can be admin')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    async def aupdate_last_message_time(self):
        return await sync_to_async(self.update_last_message_time)()

    def update_last_message_time(self):
        self.last_message_time = timezone.now()
        self.save(update_fields=['last_message_time'])

    def get_telegram_full_name(self):
        full_name = "%s %s" % (self.telegram_first_name or '', self.telegram_last_name or '')
        return full_name.strip()

    async def aget_user(self) -> User:
        return await sync_to_async(self.get_user)()

    def get_user(self) -> User:
        return self.user
