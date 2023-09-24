import re
import uuid

import jdatetime
from asgiref.sync import sync_to_async
from django.utils import timezone
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (ContextTypes, ConversationHandler, MessageHandler, filters,
                          CallbackQueryHandler, CommandHandler)

from tgbots.bots.values.admin_values import button_values, message_values
from xraypanels.models import Client
from ..enums import UserOrAdminEnum, AdminNewConfig, AdminSendMessageToUsers
from ...models import TelegramUser


class AdminMenu:
    def admin_handlers(self):
        handlers_list = list()
        create_new_config_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex(f"^{button_values['create_new_config']}$") & (self.admin_filter or None),
                               self.get_client_args)],
            states={
                AdminNewConfig.SEND_CLIENT_ARGS: [
                    CommandHandler("new", self.create_new_config, filters=self.admin_filter or None),
                    MessageHandler(filters.Regex(f"^{button_values['back_to_main_menu']}$"), self.start_menu)
                ]
            },
            fallbacks=[
                CommandHandler("start", self.start_menu),
                MessageHandler(filters.Regex(f"^{button_values['back_to_main_menu']}$"), self.start_menu),
                MessageHandler(~filters.COMMAND, self.wrong_input)],
            map_to_parent={
                UserOrAdminEnum.ADMIN: UserOrAdminEnum.ADMIN
            }

        )
        send_message_to_users_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex(f"^{button_values['send_message_to_users']}$"),
                               self.get_message_for_send_to_users)
            ],
            states={
                AdminSendMessageToUsers.SEND_DESIRED_MESSAGE: [
                    MessageHandler(~filters.COMMAND & ~filters.Regex(f"^{button_values['back_to_main_menu']}$"),
                                   self.send_message_to_users)
                ]

            },
            fallbacks=[
                CommandHandler("start", self.start_menu),
                MessageHandler(filters.Regex(f"^{button_values['back_to_main_menu']}$"), self.start_menu),
                MessageHandler(~filters.COMMAND, self.wrong_input)],
            map_to_parent={
                UserOrAdminEnum.ADMIN: UserOrAdminEnum.ADMIN
            }
        )
        handlers_list.append(create_new_config_handler)
        handlers_list.append(send_message_to_users_handler)
        handlers_list.append(
            MessageHandler(filters.Regex(f"^{button_values['user_panel']}$") & (self.admin_filter or None),
                           self.user_panel))
        return handlers_list

    async def start_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[button_values['create_new_config'], button_values['send_message_to_users']],
                    [button_values['user_panel']]]
        await update.message.reply_text(message_values['start_menu_message'],
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return UserOrAdminEnum.ADMIN

    async def get_client_args(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[button_values['back_to_main_menu']]]
        await update.message.reply_text(message_values['send_new_client_args'],
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                         one_time_keyboard=True))
        return AdminNewConfig.SEND_CLIENT_ARGS

    async def create_new_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2 or not re.findall(r'^\d{4}$', context.args[0]):
            await update.message.reply_text('آرگومان ها غیر مجاز')
            return await self.start_menu(update, context)
        price = {10: 40, 20: 70, 30: 90, 50: 115, 100: 200, 150: 270, 200: 320}
        number = context.args[0]
        total_flow = int(context.args[1])
        ip_limit = int(context.args[2]) if len(context.args) > 2 else 1
        price = context.args[3] if len(context.args) > 3 else str(price[total_flow] + ((ip_limit - 1) * 25))
        client = await Client.objects.acreate(client_uuid=uuid.uuid4(), client_name=number + '_Tel:@Sina8125',
                                              total_flow=total_flow * 1024 * 1024 * 1024, ip_limit=ip_limit,
                                              price=price)
        await client.aset_update_client()
        await client.areset_client_traffics()
        config1, config2 = client.connection_links
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
        return await self.start_menu(update, context)

    async def get_message_for_send_to_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[button_values['back_to_main_menu']]]
        await update.message.reply_text(message_values['send_message_for_send_to_users'],
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                         one_time_keyboard=True))
        return AdminSendMessageToUsers.SEND_DESIRED_MESSAGE

    async def send_message_to_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_users = await sync_to_async(list)(TelegramUser.objects.all())
        for telegram_user in telegram_users:
            try:
                await update.message.copy(chat_id=telegram_user.telegram_id)
            except Exception as e:
                print(e, file=open("tgbots/bots/bot.log", 'a+'))
                await update.message.reply_text(
                    f'خطا در ارسال پیام به {telegram_user.telegram_username or telegram_user.get_telegram_full_name() or ""}\n'
                    f'tg://openmessage?user_id={telegram_user.telegram_id}')
        return await self.start_menu(update, context)

    async def wrong_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(message_values['wrong_input_error'])
        return await self.start_menu(update, context)

    async def user_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user: TelegramUser = update.api_kwargs['user_in_model']
        if not telegram_user.telegram_is_staff or not telegram_user.is_now_admin:
            await update.message.reply_text('حساب شما ادمین نیست!')
            return await self.start_menu(update, context)
        telegram_user.is_now_admin = False
        await telegram_user.asave(update_fields=['is_now_admin'])
        return await self.start_menu(update, context)

#
# async def create_new_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#     client_number = re.findall(r'^\d{4}', update.message.text)
#     if not client_number:
#         await update.message.reply_text('ورودی شماره کلاینت اشتباه!')
#         return UserOrAdminEnum.ADMIN
#     client = Client.objects.create(client_uuid=uuid.uuid4(), client_name=client_number[0] + '_Tel:@Sina8125')
#     client.set_update_client()
#
#     keyboard = [[]]
