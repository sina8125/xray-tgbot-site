from os.path import normpath, join, splitext

import django.core.exceptions
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

from tgbots.models import TelegramUser


def default_expire_time():
    return timezone.now() + timezone.timedelta(days=30)


class Client(models.Model):
    def set_payment_receipt_image_path(instance, filename):
        print(instance.client_name)
        base, extension = splitext(filename.lower())
        return normpath(
            join(instance.client_name,
                 f'{instance.telegram_user.telegram_id or instance.user.username or ""}_{instance.purchase_date:%Y%m%d-%H%M%S}_{instance.client_uuid}{extension}'))

    user = models.ForeignKey(User, related_name='user', on_delete=models.DO_NOTHING, null=True, blank=True)
    telegram_user = models.ForeignKey(TelegramUser, related_name='telegram_user', on_delete=models.DO_NOTHING,
                                      null=True, blank=True)
    telegram_users_using_config = models.ManyToManyField(TelegramUser, 'user_using', blank=True)
    client_name = models.CharField(max_length=150, null=False, blank=False)
    client_uuid = models.UUIDField(unique=True, null=False, blank=False)
    active = models.BooleanField(default=True, blank=True, null=False)
    ip_limit = models.PositiveIntegerField(default=1, blank=True, null=False)
    total_flow = models.FloatField(default=0, blank=True, null=False)
    payment_receipt_image = models.ImageField(upload_to=set_payment_receipt_image_path, blank=True, null=True)
    price = models.PositiveIntegerField(null=True, blank=True)
    expire_time = models.DateTimeField(default=default_expire_time, blank=True, null=False)
    duration = models.DurationField(default=timezone.timedelta(days=30), blank=False, null=False)
    purchase_date = models.DateTimeField(default=timezone.now, null=False, blank=False)
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)

    def clean(self):
        if not self.user and not self.telegram_user:
            raise ValidationError('Both user and telegram_user can not be empty')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if self.telegram_user and not self.telegram_users_using_config.filter(id=self.telegram_user.id).exists():
            self.telegram_users_using_config.add(self.telegram_user)
