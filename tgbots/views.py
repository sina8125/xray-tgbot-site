import asyncio
import json
import sys

from telegram import Update

from django.views.generic import TemplateView

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import TelegramUser
from .bots.bot import tgbot

PROXY = "http://127.0.0.1:2081"


class GetConfigView(TemplateView):
    template_name = 'tgbots/tgbot.html'

    def get_context_data(self, **kwargs):
        print(self.request.headers)


class StartBot(APIView):

    def post(self, request):
        request_body = json.loads(request.body)
        print(request_body)
        update = Update.de_json(data=request_body, bot=tgbot.application.bot)
        try:
            telegram_user, created = TelegramUser.objects.update_or_create(telegram_id=update.effective_chat.id,
                                                                           defaults={
                                                                               'telegram_first_name': update.effective_chat.first_name,
                                                                               'telegram_last_name': update.effective_chat.last_name,
                                                                               'telegram_username': update.effective_chat.username
                                                                           })
            print(update.to_dict())
            update.__setstate__({'user_in_model': telegram_user})
            print(tgbot.admin_filter.user_ids)
            if telegram_user.telegram_is_staff:
                tgbot.admin_filter.add_user_ids(telegram_user.telegram_id)
            elif telegram_user.telegram_id in tgbot.admin_filter.user_ids:
                tgbot.admin_filter.remove_user_ids(telegram_user.telegram_id)

            if telegram_user.banned:
                tgbot.banned_user_filter.add_user_ids(telegram_user.telegram_id)
            elif telegram_user.telegram_id in tgbot.banned_user_filter.user_ids:
                tgbot.banned_user_filter.remove_user_ids(telegram_user.telegram_id)
        except Exception as e:
            print(e, file=open("tgbots/bots/bot.log", 'a+'))
            pass

        async def start():
            async with tgbot.application as application:
                await application.process_update(update)

        asyncio.run(start())
        return Response(status=status.HTTP_200_OK)
