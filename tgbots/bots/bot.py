import asyncio
import re
from warnings import filterwarnings

from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from telegram import Update
from telegram.ext import Application, ConversationHandler, CommandHandler, filters, ContextTypes, MessageHandler
from telegram.warnings import PTBUserWarning

from django.conf import settings

from .menus import AdminMenu, UserMenu
from .enums import UserOrAdminEnum
from ..models import TelegramUser


class XuiBot(UserMenu, AdminMenu):
    def __init__(self, bot_token: str, webhook_domain: str, proxy_url=None):
        if not bot_token or not isinstance(bot_token, str) or not re.match(r'^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$',
                                                                           bot_token):
            raise ValueError('bot token was not accepted!')
        elif not webhook_domain or not isinstance(webhook_domain, str) or not webhook_domain.startswith('https://'):
            raise ValueError('webhook domain was not accepted!')

        filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)
        self.application = Application.builder().token(bot_token)
        if proxy_url:
            self.application.proxy_url(proxy_url).get_updates_proxy_url(proxy_url)
        self.application = self.application.build()

        admin_telegram_user_id = TelegramUser.objects.filter(user__is_staff=True).values_list('telegram_id', flat=True)
        self.admin_filter = filters.User(admin_telegram_user_id)

        async def set_webhook_url():
            async with self.application as application:
                await application.bot.set_webhook(url=f'{webhook_domain}/webhook/')

        asyncio.run(set_webhook_url())
        banned_user = TelegramUser.objects.filter(banned=True).values_list('telegram_id', flat=True)
        print(banned_user)
        self.application.add_handler(MessageHandler(filters.User(banned_user), self.banned))
        self.application.add_handler(ConversationHandler(
            entry_points=[CommandHandler("start", self.start_menu)],
            states={
                UserOrAdminEnum.USER: self.user_handlers(),
                UserOrAdminEnum.ADMIN: self.admin_handlers()
            },
            fallbacks=[CommandHandler("start", self.start_menu),
                       MessageHandler(~filters.COMMAND, self.wrong_input)]
        ))

    async def start_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user: TelegramUser = update.api_kwargs['user_in_model']
        user: User = await telegram_user.aget_user()

        if user and user.is_staff and telegram_user.is_now_admin:
            return await AdminMenu.start_menu(self, update, context)
        else:
            return await UserMenu.start_menu(self, update, context)

    async def banned(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('ban')


tgbot = XuiBot(settings.TOKEN, settings.WEBHOOK_DOMAIN, settings.PROXY)
