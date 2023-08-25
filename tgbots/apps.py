import asyncio
from concurrent.futures import ProcessPoolExecutor

from django.apps import AppConfig
import subprocess
from django.conf import settings
from telegram import Bot
from telegram.ext import CommandHandler, ApplicationBuilder
from queue import Queue

from threading import Thread

from . import views
from .bot import app

TOKEN = '5976056923:AAF5UCAnNTg19EOqtJOvVdgSVBj_o-bwhKA'
PROXY = "http://127.0.0.1:2081"


# update_queue = Queue()

# def start_polling():
#     app = ApplicationBuilder().token('BOT_TOKEN').build()
#     app.add_handler(CommandHandler('start', views.start))
#     app.run_polling()


class TgbotsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tgbots'

    def ready(self):
        asyncio.run(self.set_webhook_url())

    async def set_webhook_url(self):
        async with app:
            print('hi')
            await app.bot.set_webhook(url=f'{settings.WEBHOOK_DOMAIN}/webhook/')
