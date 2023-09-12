import base64
import json

from django.contrib.auth.models import User

from .models import Client
from tgbots.models import TelegramUser


def convert_link_to_client(link: str, client_name: str, using_user: TelegramUser = None, user: User = None,
                           telgram_user: TelegramUser = None) -> Client:
    base64_link = link.removeprefix('vmess://')
    binary_format = base64.urlsafe_b64decode(link)
    config_info = json.loads(binary_format)
    client, created = Client.objects.get_or_create(client_uuid=config_info['id'],
                                                   defaults={
                                                       'user': user,
                                                       'telegram_user': telgram_user or using_user,
                                                       'client_name': client_name or config_info['ps'],
                                                   })
    if telgram_user:
        client.telegram_users_using_config.add(telgram_user)
    if using_user:
        client.telegram_users_using_config.add(using_user)

    return client


def get_client_info_from_panel():
    pass
