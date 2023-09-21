import asyncio
import json

from django.views.generic import TemplateView

from telegram import Update

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .bots.bot import app
from .models import TelegramUser

PROXY = "http://127.0.0.1:2081"


class GetConfigView(TemplateView):
    template_name = 'tgbots/tgbot.html'

    def get_context_data(self, **kwargs):
        print(self.request.headers)


class StartBot(APIView):
    def post(self, request):
        request_body = json.loads(request.body)
        update = Update.de_json(data=request_body, bot=app.application.bot)
        user, created = TelegramUser.objects.update_or_create(telegram_id=update.effective_chat.id,
                                                              defaults={
                                                                  'telegram_first_name': update.effective_user.first_name,
                                                                  'telegram_last_name': update.effective_user.last_name,
                                                                  'telegram_username': update.effective_user.username
                                                              })
        print(update.api_kwargs)
        update.__setstate__({'user_in_model': user})
        print(update.api_kwargs)

        async def start():
            async with app.application as application:
                await application.process_update(update)

        asyncio.run(start())
        return Response(status=status.HTTP_200_OK)
