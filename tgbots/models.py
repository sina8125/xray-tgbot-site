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
    telegram_id = models.PositiveBigIntegerField(unique=True, null=False, blank=False)
    telegram_username = models.CharField(max_length=32, validators=[MinLengthValidator(5)], null=True, blank=True)
    wallet_balance = models.PositiveIntegerField(null=True, blank=True)
    is_now_admin = models.BooleanField(default=False, null=True, blank=True)
    last_message_time = models.DateTimeField(auto_now=True)
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.is_now_admin and (not self.user or not self.user.is_staff):
            raise ValidationError('Only staff users can be admin')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    async def aupdate_last_message_time(self):
        return await sync_to_async(self.update_last_message_time)()

    def update_last_message_time(self):
        self.last_message_time = timezone.now()
        self.save(update_fields=['last_message_time'])
