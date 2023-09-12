import asyncio
from typing import Final

from django.conf import settings
from django.core.files.base import ContentFile
from telegram.request import HTTPXRequest
from telegram import Update, Bot, File
from telegram.ext import Application, ConversationHandler, CommandHandler, filters, ContextTypes, MessageHandler, \
    CallbackContext

from xraypanels.models import Client
from .menus import AdminMenu, UserMenu
from ..models import TelegramUser
from .enums import UserOrAdminEnum

TOKEN: Final = "5976056923:AAF5UCAnNTg19EOqtJOvVdgSVBj_o-bwhKA"
ADMIN: Final = 179102335
PROXY: Final = "http://127.0.0.1:2081"


class XuiBot(UserMenu, AdminMenu):
    def __init__(self):
        self.application = Application.builder().token(TOKEN).proxy_url(PROXY).get_updates_proxy_url(PROXY).build()

        async def set_webhook_url():
            async with self.application as application:
                await application.bot.set_webhook(url=f'{settings.WEBHOOK_DOMAIN}/webhook/')

        asyncio.run(set_webhook_url())
        self.application.add_handler(ConversationHandler(
            entry_points=[CommandHandler("start", self.start_menu)],
            states={
                UserOrAdminEnum.USER: self.user_handlers()
            },
            fallbacks=[CommandHandler("start", self.start_menu)]
        ))
        # self.application.add_handler(CommandHandler("start", self.start_menu))

    async def start_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # user = update.message.from_user.api_kwargs['user_in_model']
        if False:
            return await AdminMenu.start_menu(self, update, context)
        else:
            return await UserMenu.start_menu(self, update, context)

    # user, created = await TelegramUser.objects.aupdate_or_create(telegram_id=update.effective_user.id,
    #                                                              defaults={
    #                                                                  'telegram_first_name': update.effective_user.first_name,
    #                                                                  'telegram_last_name': update.effective_user.last_name,
    #                                                                  'telegram_username': update.effective_user.username
    #                                                              })
    # context.user_data['user_in_model'] = user

    async def say_hi(self):
        print('my')
        # print()
        await self.application.bot.initialize()
        await self.application.bot.send_message(chat_id=ADMIN, text='hi')
        # await Bot(token=TOKEN, request=HTTPXRequest(proxy_url=PROXY),
        #           get_updates_request=HTTPXRequest(proxy_url=PROXY)).send_message(chat_id=ADMIN, text='hi')
        # await a.send_message(chat_id=ADMIN, text='hi')
        # await self.application.bot.send_message(chat_id=ADMIN, text='hi', )


app = XuiBot()


def say_hi():
    print('yes')

    async def hi():
        async with app.application:
            await app.say_hi()

    asyncio.run(hi())
