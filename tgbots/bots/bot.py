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
from telegram.request import HTTPXRequest
from telegram.warnings import PTBUserWarning


from django_PTB_persistence.persistence import DjangoPersistence
from .menus import AdminMenu, UserMenu
from .enums import UserOrAdminEnum
from .values.user_values import message_values, button_values
from ..models import TelegramUser


class XuiBot(UserMenu, AdminMenu):
    def __init__(self, bot_token: str, webhook_domain: str, proxy_url=None):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.DEBUG, filename='tgbots/bots/bot.log')
        logger = logging.getLogger('xui telegram bot')
        # log_handler = handlers.TimedRotatingFileHandler('tgbots/bots/bot.log', when='D', interval=1, backupCount=2)
        # logger.setLevel(logging.DEBUG)
        # logger.addHandler(log_handler)

        if not bot_token or not isinstance(bot_token, str) or not re.match(r'^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$',
                                                                           bot_token):
            raise ValueError('bot token was not accepted!')
        elif not webhook_domain or not isinstance(webhook_domain, str) or not webhook_domain.startswith('https://'):
            raise ValueError('webhook domain was not accepted!')

        self.bot_token = bot_token
        self.webhook_domain = webhook_domain
        self.proxy_url = proxy_url
        self.application = None
        self.fallback_handlers = None
        self.admin_filter = filters.User()
        self.banned_user_filter = filters.User()
        self.bot_started = False

        asyncio.run(self.set_webhook_url())

    def start_bot(self):
        if self.bot_started:
            return
        filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

        application = Application.builder().token(self.bot_token).persistence(DjangoPersistence(namespace='x-ui'))
        if self.proxy_url:
            application = application.proxy_url(self.proxy_url).get_updates_proxy_url(self.proxy_url)
        self.application = application.build()


        self.fallback_handlers = [
            CommandHandler("start", self.start_menu),
            CallbackQueryHandler(self.start_menu, pattern=f'^{UserOrAdminEnum.BACK_TO_MAIN_MENU.value}$'),
            MessageHandler(filters.Regex(f"^{button_values['back_to_main_menu']}$"), self.start_menu),
            MessageHandler(~filters.COMMAND, self.wrong_input)]

        self.application.add_handler(MessageHandler(self.banned_user_filter, self.banned))
        self.application.add_handler(ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start_menu),
                MessageHandler(~filters.COMMAND, self.first_start),
                CallbackQueryHandler(callback=self.first_start)],
            states={
                UserOrAdminEnum.USER.value: [CallbackQueryHandler(self.start_menu,
                                                                  'back_to_main_menu')] + self.user_handlers(),
                UserOrAdminEnum.ADMIN.value: [CallbackQueryHandler(self.start_menu,
                                                                   'back_to_main_menu')] + self.admin_handlers()
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

    async def start_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user: TelegramUser = update.api_kwargs['user_in_model']
        if telegram_user.telegram_is_staff and telegram_user.is_now_admin:
            return await AdminMenu.start_menu(self, update, context)
        else:
            return await UserMenu.start_menu(self, update, context)

    async def first_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query:
            await update.callback_query.answer()
        await update.effective_chat.send_message(
            'با عرض پوزش بابت مشکل به وجود آمده\n ربات مجدد استارت شد\n لطفا گزینه مورد نظر را انتخاب کنید🙏🏻')
        return await self.start_menu(update, context)

    async def banned(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.effective_chat.send_message(message_values['banned_message'], reply_markup=ReplyKeyboardRemove())

    async def wrong_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(update.message.text)
        telegram_user = update.api_kwargs['user_in_model']
        await update.message.reply_text(message_values['wrong_input_error'])
        if not telegram_user.telegram_is_staff:
            telegram_admins = await sync_to_async(list)(TelegramUser.objects.filter(telegram_is_staff=True))
            for telegram_admin in telegram_admins:
                await context.bot.send_message(telegram_admin.telegram_id,
                                               text=f'پیام نامعتبر از:\n{telegram_user.telegram_username or telegram_user.get_telegram_full_name() or ""}\n[{telegram_user.get_telegram_full_name()}](tg://openmessage?user_id={telegram_user.telegram_id})',
                                               parse_mode='Markdown')
                await update.message.forward(telegram_admin.telegram_id)

        return await self.start_menu(update, context)

    def remove_button(self, button_data, keyboard):
        updated_keyboard = []

        for row in keyboard:
            updated_row = []
            for button in row:
                if button.callback_data != button_data:
                    updated_row.append(button)
            if updated_row:
                updated_keyboard.append(updated_row)

        return updated_keyboard


tgbot = XuiBot(settings.TOKEN, settings.WEBHOOK_DOMAIN, settings.PROXY)
