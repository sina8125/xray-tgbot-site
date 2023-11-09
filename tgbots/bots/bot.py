import asyncio
import logging
import re
from logging import handlers
from warnings import filterwarnings
from asgiref.sync import sync_to_async

from django.conf import settings

from telegram import Update, ReplyKeyboardRemove, Bot
from telegram.ext import (Application, ConversationHandler, CommandHandler, filters, ContextTypes, MessageHandler,
                          CallbackQueryHandler)
from telegram.ext.filters import BaseFilter
from telegram.request import HTTPXRequest
from telegram.warnings import PTBUserWarning

from django_PTB_persistence.persistence import DjangoPersistence
from .menus import AdminMenu, UserMenu
from .enums import UserOrAdminEnum
from .menus.menu import Menu
from .values import message_values, button_values
from ..models import TelegramUser


class XuiBot:
    def __init__(self, bot_name, bot_token: str, webhook_domain: str, proxy_url=None):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO, filename='tgbots/bots/bot.log')
        logger = logging.getLogger('xui telegram bot')
        filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

        # log_handler = handlers.TimedRotatingFileHandler('tgbots/bots/bot.log', when='D', interval=1, backupCount=2)
        # logger.setLevel(logging.DEBUG)
        # logger.addHandler(log_handler)

        # AdminMenu(self)
        self.bot_name = bot_name
        self.__user_menu: Menu = UserMenu(self)
        self.__admin_menu: Menu = AdminMenu(self)
        self.bot_token = bot_token
        self.webhook_domain = webhook_domain
        self.proxy_url = proxy_url
        self.fallback_handlers = []
        self.admin_filter = filters.User()
        self.banned_user_filter = filters.User()
        self.bot_started = False
        self.application = None

        asyncio.run(self.set_webhook_url())

    def start_bot(self):
        if self.bot_started:
            return

        application = Application.builder().token(self.bot_token).persistence(
            DjangoPersistence(namespace=self.bot_name))
        if self.proxy_url:
            application = application.proxy_url(self.proxy_url).get_updates_proxy_url(self.proxy_url)
        self.application = application.build()

        self.fallback_handlers = [
            CommandHandler("start", self.start_menu),
            CallbackQueryHandler(self.start_menu, pattern=f'^{UserOrAdminEnum.BACK_TO_MAIN_MENU.value}$'),
            MessageHandler(filters.Regex(f"^{button_values['back_to_main_menu']}$"), self.start_menu),
            MessageHandler(~filters.COMMAND, self.wrong_input)
        ]

        self.application.add_handler(MessageHandler(self.banned_user_filter, self.banned))
        self.application.add_handler(ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start_menu),
                MessageHandler(~filters.COMMAND, self.first_start),
                CallbackQueryHandler(callback=self.first_start)],
            states={
                UserOrAdminEnum.USER.value: self.user_menu.handlers(),
                UserOrAdminEnum.ADMIN.value: self.admin_menu.handlers(),
            },
            fallbacks=self.fallback_handlers,
            name='start_handler',
            persistent=True,
        ))

        self.bot_started = True

    async def set_webhook_url(self):
        proxy = HTTPXRequest(proxy_url=self.proxy_url) if self.proxy_url else None
        async with Bot(self.bot_token, request=proxy, get_updates_request=proxy) as bot:
            await bot.set_webhook(url=f'{self.webhook_domain}/webhook/')
        await proxy.shutdown()

    async def add_update(self, update: Update):
        async with self.application as application:
            await application.process_update(update)

    async def start_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user: TelegramUser = update.api_kwargs['user_in_model']
        if telegram_user.telegram_is_staff and telegram_user.is_now_admin:
            return await self.admin_menu.start_menu(update, context)
        else:
            return await self.user_menu.start_menu(update, context)

    async def first_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query:
            await update.callback_query.answer()
        await update.effective_chat.send_message(
            'با عرض پوزش بابت مشکل به وجود آمده\n ربات مجدد استارت شد\n لطفا گزینه مورد نظر را انتخاب کنید🙏🏻')
        return await self.start_menu(update, context)

    async def banned(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.effective_chat.send_message(message_values['banned_message'], reply_markup=ReplyKeyboardRemove())

    async def wrong_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user: TelegramUser = update.api_kwargs['user_in_model']
        await update.message.reply_text(message_values['wrong_input_error'])
        if not telegram_user.telegram_is_staff:
            telegram_admins = await sync_to_async(list)(TelegramUser.objects.filter(telegram_is_staff=True))
            for telegram_admin in telegram_admins:
                await context.bot.send_message(telegram_admin.telegram_id,
                                               text=f'پیام نامعتبر از:\n{telegram_user.telegram_username or telegram_user.get_telegram_full_name() or ""}\n[{telegram_user.get_telegram_full_name()}](tg://openmessage?user_id={telegram_user.telegram_id})',
                                               parse_mode='Markdown')
                await update.message.forward(telegram_admin.telegram_id)

        return await self.start_menu(update, context)

    @property
    def application(self):
        return self.__application

    @property
    def bot_name(self):
        return self.__bot_name

    @property
    def user_menu(self):
        return self.__user_menu

    @property
    def admin_menu(self):
        return self.__admin_menu

    @property
    def bot_token(self):
        return self.__bot_token

    @property
    def webhook_domain(self):
        return self.__webhook_domain

    @property
    def proxy_url(self):
        return self.__proxy_url

    @property
    def fallback_handlers(self):
        return self.__fallback_handlers

    @property
    def admin_filter(self):
        return self.__admin_filter

    @property
    def banned_user_filter(self):
        return self.__banned_user_filter

    @property
    def bot_started(self):
        return self.__bot_started

    @application.setter
    def application(self, application):
        self.__application = application

    @bot_name.setter
    def bot_name(self, bot_name: str):
        if not bot_name or not isinstance(bot_name, str):
            raise TypeError('bot name was not accepted!')
        self.__bot_name = bot_name

    @bot_token.setter
    def bot_token(self, bot_token: str):
        if not bot_token or not isinstance(bot_token, str) or not re.match(r'^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$',
                                                                           bot_token):
            raise ValueError('bot token was not accepted!')

        self.__bot_token = bot_token

    @webhook_domain.setter
    def webhook_domain(self, webhook_domain: str):
        if not webhook_domain or not isinstance(webhook_domain, str) or not webhook_domain.startswith('https://'):
            raise ValueError('webhook domain was not accepted!')
        self.__webhook_domain = webhook_domain

    @proxy_url.setter
    def proxy_url(self, proxy_url: str):
        if proxy_url is not None and (not proxy_url or not isinstance(proxy_url, str)):
            raise TypeError('proxy url was not accepted!')
        self.__proxy_url = proxy_url

    @fallback_handlers.setter
    def fallback_handlers(self, fallback_handlers: list):
        if not isinstance(fallback_handlers, list):
            raise TypeError('fallback handlers was not accepted!')
        self.__fallback_handlers = fallback_handlers

    @admin_filter.setter
    def admin_filter(self, admin_filter: filters.User):
        if not admin_filter or not isinstance(admin_filter, BaseFilter):
            raise TypeError('admin filter was not accepted!')
        self.__admin_filter = admin_filter

    @banned_user_filter.setter
    def banned_user_filter(self, banned_user_filter):
        if not banned_user_filter or not isinstance(banned_user_filter, BaseFilter):
            raise TypeError('admin filter was not accepted!')
        self.__banned_user_filter = banned_user_filter

    @bot_started.setter
    def bot_started(self, bot_started: bool):
        if not isinstance(bot_started, bool):
            raise TypeError('bot started was not accepted!')
        self.__bot_started = bot_started


tgbot = XuiBot('si2ray', settings.TOKEN, settings.WEBHOOK_DOMAIN, settings.PROXY)
