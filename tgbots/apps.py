import asyncio

from django.apps import AppConfig
from django.conf import settings

# from .views import app


class TgbotsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tgbots'

    # def ready(self):
    #     async def set_webhook_url():
    #         async with app.application as application:
    #             await application.bot.set_webhook(url=f'{settings.WEBHOOK_DOMAIN}/webhook/')
    #
    #     asyncio.run(self.set_webhook_url())
