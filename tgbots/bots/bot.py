import asyncio
from typing import Final

from django.conf import settings
from django.core.files.base import ContentFile
from telegram.request import HTTPXRequest
from telegram import Update, Bot, File
from telegram.ext import (Application, ConversationHandler, CommandHandler, filters, ContextTypes, MessageHandler,
                          CallbackContext)
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

from xraypanels.models import Client
from .menus import AdminMenu, UserMenu
from ..models import TelegramUser
from .enums import UserOrAdminEnum

TOKEN: Final = settings.TOKEN
PROXY: Final = "http://127.0.0.1:2081"


class XuiBot(UserMenu, AdminMenu):
    def __init__(self):

        filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)
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
            fallbacks=[CommandHandler("start", self.start_menu),
                       MessageHandler(~filters.COMMAND, self.wrong_input)]
        ))

    async def start_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.api_kwargs['user_in_model']
        if False:
            return await AdminMenu.start_menu(self, update, context)
        else:
            return await UserMenu.start_menu(self, update, context)


app = XuiBot()
