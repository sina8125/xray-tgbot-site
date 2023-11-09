import asyncio
import re
import uuid
import jdatetime

from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError
from django.utils import timezone

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (BaseHandler, ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler)

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
        price = context.args[3] if len(context.args) > 3 else str(price[total_flow] + ((ip_limit - 1) * 25))

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
        telegram_users = await sync_to_async(list)(TelegramUser.objects.all())
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

    def __config_info_handler(self) -> BaseHandler:
        return ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex(f"^{button_values['get_config_info']}$"), self.__get_number_or_config)
            ],
            states={
                AdminEnum.SEND_CLIENT_NUMER_OR_CONFIG.value: [
                    MessageHandler(filters.Regex(r'vmess://[\w+\-=/]+'), self.__admin_get_config_info),
                    MessageHandler(
                        filters.Regex(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'),
                        self.__admin_get_config_info),
                    MessageHandler(filters.Regex(re.compile(r'^\d{4}(_Tel:@Sina8125)?$', re.IGNORECASE)),
                                   self.__admin_get_config_info)
                ]
            },
            fallbacks=self.bot.fallback_handlers,
            map_to_parent={
                UserOrAdminEnum.ADMIN.value: UserOrAdminEnum.ADMIN.value
            },
            persistent=True,
            name='admin_config_info_handler'
        )

    async def __get_number_or_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[button_values['back_to_main_menu']]]
        await update.message.reply_text(message_values['send_config_or_uuid'],
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return AdminEnum.SEND_CLIENT_NUMER_OR_CONFIG.value

    async def __admin_get_config_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            client: Client = await self.__get_client_with_config_uuid(update.message.text,
                                                                      update.api_kwargs['user_in_model'])
        except ValidationError as e:
            if e.code == 400:
                await update.message.reply_text(message_values['vmess_or_uuid_error'])
                return await self.__get_number_or_config(update, context)
            elif e.code == 404:
                await update.message.reply_text(message_values['config_not_found_or_error'])
            else:
                print(e, file=open("tgbots/bots/bot.log", 'a+'))
                await update.message.reply_text(message_values['problem_error'])
            return await super().start_menu(update, context)

        client_status = '🟢فعال🟢' if client.active else '🔴غیرفعال🔴'
        remaining_time = "{days} روز و {H}:{M}:{S}".format(days=client.get_remaining_time.days,
                                                           H=(
                                                                   client.get_remaining_time.seconds // 3600),
                                                           M=(
                                                                     client.get_remaining_time.seconds % 3600) // 60,
                                                           S=(client.get_remaining_time.seconds % 60))
        total_flow = f'{client.get_total_flow[0]} {client.get_total_flow[1]}' if client.get_total_flow[
                                                                                     0] != 0 else 'نامحدود'
        total_remaining = f'{client.get_total_remaining[0]} {client.get_total_remaining[1]}' if client.get_total_flow[
                                                                                                    0] != 0 else 'نامحدود'
        if client.expire_time.timestamp() < 0 and client.active:
            expire_time_ad = expire_time_solar = '30 روز از زمان اتصال'
        elif client.expire_time.timestamp() == 0:
            expire_time_ad = expire_time_solar = 'نامحدود'
        else:
            expire_time_ad = client.expire_time.strftime(
                '%Y/%m/%d %H:%M:%S')
            expire_time_solar = jdatetime.datetime.fromgregorian(datetime=client.expire_time).strftime(
                '%Y/%m/%d %H:%M:%S')

        button = [
            [InlineKeyboardButton(text=client.client_name, callback_data=1),
             InlineKeyboardButton(text='👤نام اشتراک', callback_data=2)],
            [InlineKeyboardButton(text=client_status, callback_data=3),
             InlineKeyboardButton(text='🔘وضعیت', callback_data=4)],
            [InlineKeyboardButton(text=f'{client.get_total_upload[0]} {client.get_total_upload[1]}', callback_data=5),
             InlineKeyboardButton(text='🔼آپلود', callback_data=6)],
            [InlineKeyboardButton(text=f'{client.get_total_download[0]} {client.get_total_download[1]}',
                                  callback_data=7),
             InlineKeyboardButton(text='🔽دانلود', callback_data=8)],
            [InlineKeyboardButton(text=f'{client.get_total_usage[0]} {client.get_total_usage[1]}', callback_data=9),
             InlineKeyboardButton(text='🔃حجم مصرفی', callback_data=10)],
            [InlineKeyboardButton(
                text=total_flow,
                callback_data=11),
                InlineKeyboardButton(text='🔄حجم کل', callback_data=12)],
            [InlineKeyboardButton(
                text=total_remaining,
                callback_data=13),
                InlineKeyboardButton(text='🔁حجم باقی مانده', callback_data=14)],
            [InlineKeyboardButton(text=expire_time_ad, callback_data=15),
             InlineKeyboardButton(text='📅تاریخ اتمام(میلادی)', callback_data=16)],
            [InlineKeyboardButton(
                text=expire_time_solar,
                callback_data=17),
                InlineKeyboardButton(text='📅تاریخ اتمام(شمسی)', callback_data=18)],
            [InlineKeyboardButton(text=remaining_time if client.expire_time.timestamp() != 0 else 'نامحدود',
                                  callback_data=19),
             InlineKeyboardButton(text='⏳زمان باقی مانده', callback_data=20)],
            [InlineKeyboardButton(text=button_values['back_to_main_menu'],
                                  callback_data=str(UserOrAdminEnum.BACK_TO_MAIN_MENU.value))]
        ]
        waiting_message = await update.message.reply_text('⏳')
        await asyncio.sleep(2)
        await waiting_message.delete()
        await update.message.reply_text(message_values['config_info_message'],
                                        reply_markup=InlineKeyboardMarkup(button))
        return UserOrAdminEnum.USER.value

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
