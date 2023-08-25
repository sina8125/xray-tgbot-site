import asyncio
import json

from django.views.generic import TemplateView

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, Updater, ContextTypes, Application

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .bot import app

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
        asyncio.run(self.start(request))
        return Response(status=status.HTTP_200_OK)

    async def start(self, request):
        async with app:
            await app.process_update(Update.de_json(data=json.loads(request.body), bot=app.bot))
