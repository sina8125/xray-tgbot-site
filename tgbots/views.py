import asyncio
import json

from telegram import Update

from django.views.generic import TemplateView

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .bots.values import message_values
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
        update = Update.de_json(data=request_body, bot=tgbot.application.bot)
        telegram_user, created = TelegramUser.objects.update_or_create(telegram_id=update.effective_chat.id,
                                                                       defaults={
                                                                           'telegram_first_name': update.effective_user.first_name,
                                                                           'telegram_last_name': update.effective_user.last_name,
                                                                           'telegram_username': update.effective_user.username
                                                                       })
        update.__setstate__({'user_in_model': telegram_user})
        if telegram_user.user and telegram_user.user.is_staff:
            if telegram_user.telegram_id not in tgbot.admin_filter.user_ids:
                tgbot.admin_filter.add_user_ids(telegram_user.telegram_id)
        elif telegram_user.telegram_id in tgbot.admin_filter.user_ids:
            tgbot.admin_filter.remove_user_ids(telegram_user.telegram_id)

        async def start():
            async with tgbot.application as application:
                # if telegram_user.banned:
                #     await application.bot.send_message(update.effective_user.id, message_values[''])
                await application.process_update(update)

        asyncio.run(start())
        return Response(status=status.HTTP_200_OK)
