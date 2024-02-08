import asyncio
import re
import uuid
import jdatetime

from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError
from django.utils import timezone

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (BaseHandler, ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler,
                          CallbackQueryHandler)

from .menu import Menu
from tgbots.bots.values import message_values, button_values
from xraypanels.models import Client
from ..enums import UserOrAdminEnum, AdminEnum
from ...models import TelegramUser


class AdminMenu(Menu):

    def __init__(self, bot):
        super().__init__(bot)

    def handlers(self):
        handlers_list = [
            self.__create_new_config_handler(),
            self.__renewal_config_handler(),
            self.__send_message_to_users_handler(),
            self.__config_info_handler(),

            self.__user_panel_handler()
        ]
        return handlers_list

    async def start_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [button_values['create_new_config'], button_values['renewal_config']],
            [button_values['send_message_to_users'], button_values['get_config_info']],
            [button_values['user_panel']]
        ]

        if update.callback_query:
            await update.callback_query.answer()
            if update.callback_query.data == str(UserOrAdminEnum.BACK_TO_MAIN_MENU.value):
                inline_keyboard = InlineKeyboardMarkup(self.remove_button(update.callback_query.data,
                                                                          update.callback_query.message.reply_markup.inline_keyboard))
                await update.callback_query.edit_message_reply_markup(inline_keyboard)

        await update.effective_chat.send_message(message_values['admin_start_menu_message'],
                                                 reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return UserOrAdminEnum.ADMIN.value

    # ---------------------------------
    # Create New Config Section
    def __create_new_config_handler(self) -> BaseHandler:
        return ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex(f"^{button_values['create_new_config']}$"),
                               self.__get_client_args)],
            states={
                AdminEnum.SEND_CLIENT_ARGS.value: [
                    CommandHandler("new", self.__create_new_config, filters=self.bot.admin_filter or None)
                ]
            },
            fallbacks=self.bot.fallback_handlers,
            map_to_parent={
                UserOrAdminEnum.ADMIN.value: UserOrAdminEnum.ADMIN.value
            },
            name='admin_new_config_handler',
            persistent=True
        )

    async def __get_client_args(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[button_values['back_to_main_menu']]]
        await update.message.reply_text(message_values['send_new_client_args'],
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return AdminEnum.SEND_CLIENT_ARGS.value

    async def __create_new_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        match = re.match(r'^\d{4}', context.args[0]) if len(context.args) >= 2 else None
        if len(context.args) < 2 or not match:
            await update.message.reply_text('آرگومان ها غیر مجاز')
            return await self.__get_client_args(update, context)

        price = {10: 40, 20: 70, 30: 90, 50: 115, 100: 200, 150: 270, 200: 320}
        number = match.group(0)
        client_name = number + '_Tel:@Sina8125'
        total_flow = int(context.args[1])
        ip_limit = int(context.args[2]) if len(context.args) > 2 else 1
        price = int(context.args[3]) if len(context.args) > 3 else price[total_flow] + ((ip_limit - 1) * 25)

        try:
            # update previous client
            previous_client, created = await Client.aget_client_with_client_name(client_name=client_name)
            previous_client.active = False
            if previous_client.expire_time > timezone.now():
                previous_client.expire_time = timezone.now()
            await previous_client.asave(update_fields=['active', 'expire_time'])
        except Exception as e:
            pass
        client = await Client.objects.acreate(client_uuid=uuid.uuid4(), client_name=client_name,
                                              total_flow=total_flow * 1024 * 1024 * 1024, ip_limit=ip_limit,
                                              price=price)
        await client.aset_update_client()
        await client.areset_client_traffics()
        config1, config2 = client.connection_links
        if not config1:
            await update.message.reply_text(message_values['config_not_found_or_error'])
            return await self.__get_client_args(update, context)

        expire_time_ad = client.expire_time.strftime('%Y/%m/%d')
        expire_time_solar = jdatetime.datetime.fromgregorian(datetime=client.expire_time).strftime('%Y/%m/%d')
        await update.message.reply_text(
            message_values['new_config_message'].format(config1=config1,
                                                        config2=config2,
                                                        client_name=client.client_name.replace('_', '\_'),
                                                        expire_time_ad=expire_time_ad,
                                                        expire_time_solar=expire_time_solar,
                                                        ip_limit=client.ip_limit,
                                                        total_flow=f'{int(client.get_total_flow[0])} {client.get_total_flow[1]}',
                                                        price=client.price
                                                        ), parse_mode="Markdown")
        return await self.__get_client_args(update, context)

    # ---------------------------------

    # ---------------------------------
    # Renewal Config Section
    def __renewal_config_handler(self) -> BaseHandler:
        return ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex(f"^{button_values['renewal_config']}$"),
                               self.__get_client_args)],
            states={
                AdminEnum.SEND_CLIENT_ARGS.value: [
                    CommandHandler("new", self.__renewal_config, filters=self.bot.admin_filter or None)
                ]
            },
            fallbacks=self.bot.fallback_handlers,
            map_to_parent={
                UserOrAdminEnum.ADMIN.value: UserOrAdminEnum.ADMIN.value
            },
            name='admin_renewal_config_handler',
            persistent=True
        )

    async def __renewal_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        match = re.match(r'^\d{4}', context.args[0]) if len(context.args) >= 2 else None
        if len(context.args) < 2 or not match:
            await update.message.reply_text('آرگومان ها غیر مجاز')
            return await self.__get_client_args(update, context)

        price = {10: 40, 20: 70, 30: 90, 50: 115, 100: 200, 150: 270, 200: 320}
        number = match.group(0)
        client_name = number + '_Tel:@Sina8125'
        total_flow = int(context.args[1])
        ip_limit = int(context.args[2]) if len(context.args) > 2 else 1
        price = int(context.args[3]) if len(context.args) > 3 else price[total_flow] + ((ip_limit - 1) * 25)

        client, created = await Client.aget_client_with_client_name(client_name=client_name)
        sum_price = (client.price + price) if client.price else price
        await client.aset_update_client(total_flow=total_flow * 1024 * 1024 * 1024,
                                        ip_limit=ip_limit,
                                        enable=True,
                                        expire_time=timezone.now() + timezone.timedelta(days=30),
                                        price=sum_price)
        await client.areset_client_traffics()
        config1, config2 = client.connection_links
        if not config1:
            await update.message.reply_text(message_values['config_not_found_or_error'])
            return await self.__get_client_args(update, context)

        expire_time_ad = client.expire_time.strftime('%Y/%m/%d')
        expire_time_solar = jdatetime.datetime.fromgregorian(datetime=client.expire_time).strftime('%Y/%m/%d')
        await update.message.reply_text(
            message_values['new_config_message'].format(config1=config1,
                                                        config2=config2,
                                                        client_name=client.client_name.replace('_', '\_'),
                                                        expire_time_ad=expire_time_ad,
                                                        expire_time_solar=expire_time_solar,
                                                        ip_limit=client.ip_limit,
                                                        total_flow=f'{int(client.get_total_flow[0])} {client.get_total_flow[1]}',
                                                        price=price
                                                        ), parse_mode="Markdown")
        return await super().start_menu(update, context)

    # ---------------------------------

    # ---------------------------------
    # Send Message To Users Section
    def __send_message_to_users_handler(self) -> BaseHandler:
        return ConversationHandler(
            entry_points=[
                MessageHandler(
                    filters.Regex(f"^{button_values['send_message_to_users']}$") & (self.bot.admin_filter or None),
                    self.__get_message_for_send_to_users)
            ],
            states={
                AdminEnum.SEND_DESIRED_MESSAGE.value: [
                    MessageHandler(~filters.COMMAND & ~filters.Regex(f"^{button_values['back_to_main_menu']}$") & (
                            self.bot.admin_filter or None),
                                   self.__send_message_to_users)
                ]

            },
            fallbacks=self.bot.fallback_handlers,
            map_to_parent={
                UserOrAdminEnum.ADMIN.value: UserOrAdminEnum.ADMIN.value
            },
            name='admin_send_message_handler',
            persistent=True
        )

    async def __get_message_for_send_to_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[button_values['back_to_main_menu']]]
        await update.message.reply_text(message_values['send_message_for_send_to_users'],
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return AdminEnum.SEND_DESIRED_MESSAGE.value

    async def __send_message_to_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_users = await sync_to_async(list)(TelegramUser.objects.filter(banned=False))
        for telegram_user in telegram_users:
            try:
                await update.message.copy(chat_id=telegram_user.telegram_id, reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(button_values['back_to_main_menu'],
                                           callback_data=str(UserOrAdminEnum.BACK_TO_MAIN_MENU.value))]]))
            except Exception as e:
                print(e, file=open("tgbots/bots/bot.log", 'a+'))
                await update.message.reply_text(
                    f'خطا در ارسال پیام به {telegram_user.telegram_username or telegram_user.get_telegram_full_name() or ""}\n'
                    f'tg://openmessage?user_id={telegram_user.telegram_id}')
        return await super().start_menu(update, context)

    # ---------------------------------

    # ---------------------------------
    # Admin Get Config And User Info Section
    def __config_info_handler(self) -> BaseHandler:
        return ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex(f"^{button_values['get_config_info']}$"), self.__get_number_or_config)
            ],
            states={
                AdminEnum.SEND_CLIENT_NUMER_OR_CONFIG.value: [
                    MessageHandler(filters.Regex(r'vmess://[\w+\-=/]+'), self.__config_info_with_uuid),
                    MessageHandler(
                        filters.Regex(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'),
                        self.__config_info_with_uuid),
                    MessageHandler(filters.Regex(re.compile(r'^\d{4}(_Tel:@Sina8125)?$', re.IGNORECASE)),
                                   self.__config_info_with_number)
                ],
                AdminEnum.GET_CLIENT_TELEGRAM_USER.value: [
                    CallbackQueryHandler(self.__get_client_telegram_user_info, re.compile(r'^telegram_user_\d+$'))
                ]
            },
            fallbacks=self.bot.fallback_handlers,
            map_to_parent={
                UserOrAdminEnum.ADMIN.value: UserOrAdminEnum.ADMIN.value
            },
            persistent=True,
            name='admin_config_info_handler',
            per_user=True
        )

    async def __get_number_or_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[button_values['back_to_main_menu']]]
        await update.message.reply_text(message_values['send_config_to_get_info'],
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return AdminEnum.SEND_CLIENT_NUMER_OR_CONFIG.value

    async def __config_info_with_uuid(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        waiting_message = await update.message.reply_text('⏳')
        await asyncio.sleep(2)
        try:
            client: Client = await self._get_client_with_config_uuid(update.message.text)
        except ValidationError as e:
            await waiting_message.delete()
            return await self._get_client_exception_handler(e, update, context, self.__get_number_or_config)

        response = await self.__admin_get_config_info(client, update, context)
        await waiting_message.delete()
        return response

    async def __config_info_with_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        waiting_message = await update.message.reply_text('⏳')
        await asyncio.sleep(2)
        try:
            client: Client = await self._get_client_with_config_name(update.message.text)
        except ValidationError as e:
            await waiting_message.delete()
            return await self._get_client_exception_handler(e, update, context, self.__get_number_or_config)

        response = await self.__admin_get_config_info(client, update, context)
        await waiting_message.delete()
        return response

    async def __admin_get_config_info(self, client: Client, update: Update, context: ContextTypes.DEFAULT_TYPE):
        button = self._config_info_message_inline_keyboard(client)
        if client.telegram_user:
            button.insert(
                -1,
                [
                    InlineKeyboardButton(str(client.telegram_user),
                                         callback_data=f'telegram_user_{client.telegram_user.pk}', ),
                    InlineKeyboardButton('کاربر:', callback_data='-1')
                ])
        await update.message.reply_text(message_values['config_info_message'],
                                        reply_markup=InlineKeyboardMarkup(button))
        return AdminEnum.GET_CLIENT_TELEGRAM_USER.value

    async def __get_client_telegram_user_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        client_telegram_user_pk = re.match(r'^telegram_user_(\d+)$', update.callback_query.data)
        client_telegram_user = await TelegramUser.objects.aget(pk=int(client_telegram_user_pk.group(1)))
        button = [
            [
                InlineKeyboardButton(text=''),
                InlineKeyboardButton(text='نام:')
            ]
        ]
        await update.effective_chat.send_message(str(client_telegram_user))
        return UserOrAdminEnum.ADMIN.value

    # ---------------------------------

    # User Panel Section
    # ---------------------------------
    def __user_panel_handler(self) -> BaseHandler:
        return MessageHandler(filters.Regex(f"^{button_values['user_panel']}$") & (self.bot.admin_filter or None),
                              self.__user_panel)

    async def __user_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user: TelegramUser = update.api_kwargs['user_in_model']
        if not telegram_user.telegram_is_staff or not telegram_user.is_now_admin:
            await update.message.reply_text('حساب شما ادمین نیست!')
            return await super().start_menu(update, context)
        telegram_user.is_now_admin = False
        await telegram_user.asave(update_fields=['is_now_admin'])
        return await super().start_menu(update, context)
    # ---------------------------------
