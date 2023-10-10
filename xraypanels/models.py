import base64
import json
from datetime import timedelta
from os.path import normpath, join, splitext
from uuid import UUID

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
    inbound_name = models.CharField(max_length=150, null=True, blank=False)
    active = models.BooleanField(default=True, null=True, blank=True)
    port = models.PositiveIntegerField(blank=False, null=False, unique=True)
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inbounds'
        verbose_name = 'Inbound'
        verbose_name_plural = 'Inbounds'

    def __str__(self):
        return str(self.inbound_id)


class Client(models.Model):
    def set_payment_receipt_image_path(self, filename):
        base, extension = splitext(filename.lower())
        return normpath(
            join(self.client_name,
                 f'{self.telegram_user.telegram_id or self.user.username or ""}_{self.purchase_date:%Y%m%d-%H%M%S}_{self.client_uuid}{extension}'))

    user = models.ForeignKey(User, related_name='user', on_delete=models.SET_NULL, null=True, blank=True)
    telegram_user = models.ForeignKey(TelegramUser, related_name='telegram_user', on_delete=models.SET_NULL,
                                      null=True, blank=True)
    telegram_users_using_config = models.ManyToManyField(TelegramUser, 'user_using', db_table='users_using_clients',
                                                         blank=True)
    client_inbound = models.ForeignKey(Inbound, related_name='inbound', on_delete=models.SET_NULL, null=True,
                                       blank=True)
    client_name = models.CharField(max_length=150, null=True, blank=True)
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

    class Meta:
        db_table = 'clients'
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'

    def __str__(self):
        return self.client_name or str(self.client_uuid)

    @property
    def connection_links(self):
        if not self.client_inbound or not self.client_name:
            return None, None

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
        if self.expire_time > timezone.now():
            return self.expire_time - timezone.now()
        elif self.expire_time.timestamp() < 0:
            return self.duration
        else:
            return timedelta(days=0)

    def save(self, *args, **kwargs):
        # if not self.user and not self.telegram_user:
        #     raise ValidationError('Both user and telegram_user can not be empty')
        # if (self.expire_time and self.expire_time <= timezone.now()) or self.total_usage >= self.total_flow:
        #     self.active = False
        super().save(*args, **kwargs)
        if self.telegram_user:
            self.telegram_users_using_config.add(self.telegram_user)

    @classmethod
    @panel.login_decorator
    def get_client_with_client_name(cls, client_name, telegram_user: TelegramUser = None):
        client_traffics, client, inbound = panel.get_client_traffics_by_email(email=client_name)
        if not client:
            raise ValidationError('client not found!')
        client_inbound, created = Inbound.objects.update_or_create(inbound_id=inbound['id'],
                                                                   defaults={
                                                                       'inbound_name': inbound['remark'],
                                                                       'active': inbound['enable'],
                                                                       'port': inbound['port']
                                                                   })
        client_model, created = cls.objects.update_or_create(client_uuid=client['id'],
                                                             defaults={
                                                                 'client_inbound': client_inbound,
                                                                 'client_name': client_traffics['email'],
                                                                 'active': client_traffics['enable'] and client[
                                                                     'enable'] and inbound['enable'],
                                                                 'total_upload': client_traffics['up'],
                                                                 'total_download': client_traffics['down'],
                                                                 'total_flow': client_traffics['total'],
                                                                 'expire_time': datetime.fromtimestamp(
                                                                     client_traffics['expiryTime'] / 1000,
                                                                     tz=timezone.get_default_timezone()),
                                                                 'total_usage': client_traffics['up'] + client_traffics[
                                                                     'down'],
                                                                 'ip_limit': client['limitIp']
                                                             })
        if telegram_user and (created or not client_model.telegram_user):
            client_model.telegram_user = telegram_user
            client_model.save(update_fields=['telegram_user'])

        return client_model, created

    @classmethod
    async def aget_client_with_client_name(cls, client_name, telegram_user: TelegramUser = None):
        return await sync_to_async(cls.get_client_with_client_name)(
            client_name=client_name,
            telegram_user=telegram_user
        )

    @classmethod
    @panel.login_decorator
    def get_client_with_uuid(cls, client_uuid, telegram_user: TelegramUser = None):
        client_traffics, client, inbound = panel.get_client_traffics_by_uuid(uuid=client_uuid)
        if not client:
            raise ValidationError('client not found!')
        client_inbound, created = Inbound.objects.update_or_create(inbound_id=inbound['id'],
                                                                   defaults={
                                                                       'inbound_name': inbound['remark'],
                                                                       'active': inbound['enable'],
                                                                       'port': inbound['port']
                                                                   })
        client_model, created = cls.objects.update_or_create(client_uuid=client['id'],
                                                             defaults={
                                                                 'client_inbound': client_inbound,
                                                                 'client_name': client_traffics['email'],
                                                                 'active': client_traffics['enable'] and client[
                                                                     'enable'] and inbound['enable'],
                                                                 'total_upload': client_traffics['up'],
                                                                 'total_download': client_traffics['down'],
                                                                 'total_flow': client_traffics['total'],
                                                                 'expire_time': datetime.fromtimestamp(
                                                                     client_traffics['expiryTime'] / 1000,
                                                                     tz=timezone.get_default_timezone()),
                                                                 'total_usage': client_traffics['up'] + client_traffics[
                                                                     'down'],
                                                                 'ip_limit': client['limitIp']
                                                             })
        if telegram_user and (created or not client_model.telegram_user):
            client_model.telegram_user = telegram_user
            client_model.save(update_fields=['telegram_user'])

        return client_model, created

    @classmethod
    async def aget_client_with_uuid(cls, client_uuid, telegram_user: TelegramUser = None):
        return await sync_to_async(cls.get_client_with_uuid)(
            client_uuid=client_uuid,
            telegram_user=telegram_user
        )

    @panel.login_decorator
    def get_update_client(self, client_traffics=None, client=None, inbound=None):
        if not client_traffics or not client or not inbound:
            client_traffics, client, inbound = panel.get_client_traffics_by_uuid(uuid=str(self.client_uuid),
                                                                                 inbound_id=self.client_inbound.inbound_id if self.client_inbound else None)
        if not client:
            raise ValidationError('client not found!')

        self.client_inbound, created = Inbound.objects.update_or_create(inbound_id=inbound['id'],
                                                                        defaults={
                                                                            'inbound_name': inbound['remark'],
                                                                            'active': inbound['enable'],
                                                                            'port': inbound['port']
                                                                        })
        self.active = client_traffics['enable'] and client['enable'] and inbound['enable']
        self.client_name = client_traffics['email']
        self.total_upload = client_traffics['up']
        self.total_download = client_traffics['down']
        self.total_flow = client_traffics['total']
        self.expire_time = datetime.fromtimestamp(client_traffics['expiryTime'] / 1000,
                                                  tz=timezone.get_default_timezone())
        self.total_usage = self.total_download + self.total_upload
        self.ip_limit = client['limitIp']
        self.save()

    async def aget_update_client(self, client_traffics=None, client=None, inbound=None):
        return await sync_to_async(self.get_update_client)(
            client_traffics=client_traffics,
            client=client,
            inbound=inbound
        )

    @panel.login_decorator
    def set_update_client(self, client_name: str = None, client_uuid: UUID = None, inbound_id: int = None,
                          total_flow: int = None, ip_limit: int = None, enable: bool = None,
                          expire_time: datetime = None, price: int = None):
        self.__dict__.update({key: value for key, value in locals().items() if value is not None})

        client_traffics, client, inbound = panel.update_client(email=self.client_name,
                                                               uuid=str(self.client_uuid),
                                                               inbound_id=self.client_inbound.inbound_id if self.client_inbound else None,
                                                               total_gb=self.total_flow,
                                                               ip_limit=self.ip_limit,
                                                               enable=self.active,
                                                               expire_time=int(self.expire_time.astimezone(
                                                                   tz=timezone.get_default_timezone()).timestamp() * 1000)
                                                               )
        if not client:
            raise ValidationError('client update error!')
        self.get_update_client()
        # self.save()

    async def aset_update_client(self, client_name: str = None, client_uuid: UUID = None, inbound_id: int = None,
                                 total_flow: int = None, ip_limit: int = None, enable: bool = None,
                                 expire_time: datetime = None, price: int = None):
        return await sync_to_async(self.set_update_client)(
            **{key: value for key, value in locals().items() if (key != 'self' and value is not None)})

    @panel.login_decorator
    def reset_client_traffics(self):
        reset_request = panel.reset_client_traffics(email=self.client_name,
                                                    uuid=str(self.client_uuid),
                                                    inbound_id=self.client_inbound.inbound_id if self.client_inbound else None)
        if not reset_request:
            raise ValidationError('reset client traffic error!')
        self.total_usage = 0
        self.total_upload = 0
        self.total_download = 0
        self.save(update_fields=['total_usage', 'total_upload', 'total_download'])

    async def areset_client_traffics(self):
        return await sync_to_async(self.reset_client_traffics)()

    @panel.login_decorator
    def add_client(self):
        if not self.client_inbound:
            raise ValidationError('inbound id must be not null for add client!\nplease set inbound id for client')
        if not self.client_name:
            raise ValidationError('client must have a client name!')
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
        self.get_update_client()
