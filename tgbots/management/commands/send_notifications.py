import asyncio

from django.core.management.base import BaseCommand
from django.utils import timezone

from tgbots.bots.bot import app


class Command(BaseCommand):

    def handle(self, *args, **options):
        asyncio.run(app.say_hi())
