import base64
import json
from os.path import normpath, join, splitext

import django.core.exceptions
from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.datetime_safe import datetime

from tgbots.models import TelegramUser
from .xuipanels.xui import panel


def default_expire_time():
    return timezone.now() + timezone.timedelta(days=30)


def convert_bytes(num):
    units = ['بایت', 'کیلوبایت', 'مگابایت', 'گیگابایت']
    for unit in units:
        if num < 1024:
            return round(num, 2), unit
        num /= 1024
    return round(num, 2), 'ترابایت'


class Inbound(models.Model):
    inbound_id = models.PositiveIntegerField(blank=False, null=False, unique=True)
    port = models.PositiveIntegerField(blank=False, null=False, unique=True)


class Client(models.Model):
    def set_payment_receipt_image_path(self, filename):
        base, extension = splitext(filename.lower())
        return normpath(
            join(self.client_name,
                 f'{self.telegram_user.telegram_id or self.user.username or ""}_{self.purchase_date:%Y%m%d-%H%M%S}_{self.client_uuid}{extension}'))

    user = models.ForeignKey(User, related_name='user', on_delete=models.DO_NOTHING, null=True, blank=True)
    telegram_user = models.ForeignKey(TelegramUser, related_name='telegram_user', on_delete=models.DO_NOTHING,
                                      null=True, blank=True)
    telegram_users_using_config = models.ManyToManyField(TelegramUser, 'user_using', blank=True)
    client_inbound = models.ForeignKey(Inbound, related_name='inbound', on_delete=models.DO_NOTHING, null=True,
                                       blank=True)
    client_name = models.CharField(max_length=150, null=True, blank=False)
    client_uuid = models.UUIDField(unique=True, null=False, blank=False)
    active = models.BooleanField(default=True, blank=True, null=False)
    ip_limit = models.PositiveIntegerField(default=1, blank=True, null=False)
    total_flow = models.PositiveBigIntegerField(default=0, blank=True, null=False)
    total_download = models.PositiveBigIntegerField(default=0, blank=True, null=True)
    total_upload = models.PositiveBigIntegerField(default=0, blank=True, null=True)
    total_usage = models.PositiveBigIntegerField(default=0, blank=True, null=True)
    payment_receipt_image = models.ImageField(upload_to=set_payment_receipt_image_path, blank=True, null=True)
    price = models.PositiveIntegerField(null=True, blank=True)
    expire_time = models.DateTimeField(default=default_expire_time, blank=True, null=False)
    duration = models.DurationField(default=timezone.timedelta(days=30), blank=False, null=False)
    purchase_date = models.DateTimeField(default=timezone.now, null=False, blank=False)
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.user and not self.telegram_user:
            raise ValidationError('Both user and telegram_user can not be empty')
        # if (self.expire_time and self.expire_time <= timezone.now()) or self.total_usage >= self.total_flow:
        #     self.active = False
        super().save(*args, **kwargs)
        if self.telegram_user and not self.telegram_users_using_config.filter(id=self.telegram_user.id).exists():
            self.telegram_users_using_config.add(self.telegram_user)

    def get_update_client(self):
        client_request = panel.get_client_traffics_by_uuid(uuid=str(self.client_uuid),
                                                           inbound_id=self.client_inbound.inbound_id if self.client_inbound else None)
        if not client_request:
            raise ValidationError('client not found!')
        client_traffics, client, inbound = client_request
        if not self.client_inbound or self.client_inbound.inbound_id != inbound['id']:
            self.client_inbound, created = Inbound.objects.get_or_create(inbound_id=inbound['id'],
                                                                         defaults={'port': inbound['port']})
        self.active = client_traffics['enable'] and client['enable']
        self.client_name = client_traffics['email']
        self.total_upload = client_traffics['up']
        self.total_download = client_traffics['down']
        self.total_flow = client_traffics['total']
        self.expire_time = datetime.fromtimestamp(client_traffics['expiryTime'] / 1000,
                                                  tz=timezone.get_default_timezone())
        self.total_usage = self.total_download + self.total_upload
        self.ip_limit = client['limitIp']
        self.save()

    async def aget_update_client(self):
        return await sync_to_async(self.get_update_client)()

    def set_update_client(self):
        update_request = panel.update_client(email=self.client_name,
                                             uuid=str(self.client_uuid),
                                             inbound_id=self.client_inbound.inbound_id if self.client_inbound else None,
                                             total_gb=self.total_flow,
                                             ip_limit=self.ip_limit,
                                             enable=self.active,
                                             expire_time=int(self.expire_time.astimezone(
                                                 tz=timezone.get_default_timezone()).timestamp() * 1000)
                                             )
        if not update_request:
            raise ValidationError('client update error!')
        self.save()

    def add_client(self):
        if not self.client_inbound:
            raise ValidationError('inbound id must be not null for add client!\nplease set inbound id for client')
        add_request = panel.add_client(inbound_id=self.client_inbound.inbound_id,
                                       email=self.client_name,
                                       uuid=str(self.client_uuid),
                                       total_gb=self.total_flow,
                                       expire_time=int(self.expire_time.astimezone(
                                           tz=timezone.get_default_timezone()).timestamp() * 1000),
                                       ip_limit=self.ip_limit,
                                       enable=self.active)
        if not add_request:
            raise ValidationError('add client error!')
        self.save()

    @property
    def connection_links(self):
        def create_link(address, host, operator):
            vmess_config = {
                "add": f"{address}.sinarahimi.tk",
                "aid": "0",
                "alpn": "",
                "fp": "",
                "host": f"{host}",
                "id": f"{str(self.client_uuid)}",
                "net": "tcp",
                "path": "/",
                "port": f"{self.client_inbound.port}",
                "ps": f"{self.client_name} {operator}",
                "scy": "auto",
                "sni": "",
                "tls": "",
                "type": "http",
                "v": "2"
            }
            vmess_base64 = base64.urlsafe_b64encode(json.dumps(vmess_config).encode()).decode()
            vmess_link = f"vmess://{vmess_base64}"
            return vmess_link

        header1 = "telewebion.com"
        header2 = "zula.ir"
        config1 = create_link("mci", header1, "(Hamrah Aval)")
        config2 = create_link("mtn", header2, "(Irancell)")
        return config1, config2

    @property
    def get_total_flow(self):
        return convert_bytes(self.total_flow)

    @property
    def get_total_download(self):
        return convert_bytes(self.total_download)

    @property
    def get_total_upload(self):
        return convert_bytes(self.total_upload)

    @property
    def get_total_usage(self):
        return convert_bytes(self.total_usage)

    @property
    def get_total_remaining(self):
        if self.total_flow >= self.total_usage:
            return convert_bytes(self.total_flow - self.total_usage)
        else:
            return 0, 'بایت'

    @property
    def get_remaining_time(self):
        return self.expire_time - timezone.now()
