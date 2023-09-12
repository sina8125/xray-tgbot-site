import asyncio
import json

from django.views.generic import TemplateView

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, Updater, ContextTypes, Application

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


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = "به ربات دریافت کانفیگ خوش آمدید\nاین ربات جهت بروزرسانی کانفیگ ایجاد شده\nدر صورت بروز مشکل با پشتیبانی در ارتباط باشید\n@Sina8125"
    await update.message.reply_text(message)


class StartBot(APIView):
    def post(self, request):
        print(request.body)
        request_body = json.loads(request.body)
        # print()
        # user = TelegramUser.objects.get(telegram_id=request_body['message']['from']['id'])
        # user.update_last_message_time()
        user, created = TelegramUser.objects.update_or_create(telegram_id=request_body['message']['from']['id'],
                                                              defaults={
                                                                  'telegram_first_name': request_body['message'][
                                                                      'from'].get(
                                                                      'first_name'),
                                                                  'telegram_last_name': request_body['message'][
                                                                      'from'].get(
                                                                      'last_name'),
                                                                  'telegram_username': request_body['message'][
                                                                      'from'].get(
                                                                      'username')
                                                              })
        request_body['message']['from']['user_in_model'] = user
        update = Update.de_json(data=request_body, bot=app.application.bot)

        # print(app.hi)
        async def start():
            async with app.application as application:
                await application.process_update(update)

        asyncio.run(start())
        return Response(status=status.HTTP_200_OK)
