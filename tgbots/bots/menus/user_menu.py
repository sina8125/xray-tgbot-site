import asyncio
import base64
import json
import re

import jdatetime
from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError
from django.utils import timezone
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (ContextTypes, ConversationHandler, MessageHandler, filters,
                          CallbackQueryHandler)

from xraypanels.models import Client
from ..enums import UserOrAdminEnum, UserUpdatedConfig, UserConfigInfo
from tgbots.models import TelegramUser
from ..values.user_values import button_values, message_values


class UserMenu:
    def user_handlers(self):
        handlers_list = list()
        update_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex(f"^{button_values['get_updated_config']}$"), self.get_update_config)],
            states={
                UserUpdatedConfig.SEND_CONFIG: [
                    MessageHandler(filters.Regex(r'vmess://[\w+\-=/]+'), self.create_update_config),
                    MessageHandler(
                        filters.Regex(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'),
                        self.create_update_config)
                ]},
            fallbacks=[MessageHandler(filters.Regex(f"^{button_values['back_to_main_menu']}$"), self.start_menu),
                       MessageHandler(~filters.COMMAND, self.wrong_input)],
            map_to_parent={
                UserOrAdminEnum.USER: UserOrAdminEnum.USER
            }
        )
        config_info_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex(f"^{button_values['get_config_info']}$"), self.get_config_info)
            ],
            states={
                UserConfigInfo.SEND_CONFIG: [
                    MessageHandler(filters.Regex(r'vmess://[\w+\-=/]+'), self.config_info),
                    MessageHandler(
                        filters.Regex(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'),
                        self.config_info),
                    MessageHandler(filters.Regex(f"^{button_values['back_to_main_menu']}$"), self.start_menu)
                ],
                UserConfigInfo.BACK_TO_MENU: [
                    CallbackQueryHandler(self.start_menu, pattern=str(UserConfigInfo.BACK_TO_MENU)),
                    MessageHandler(filters.Regex(f"^{button_values['back_to_main_menu']}$"), self.start_menu)
                ]
            },
            fallbacks=[MessageHandler(~filters.COMMAND, self.wrong_input)]
            ,
            map_to_parent={
                UserOrAdminEnum.USER: UserOrAdminEnum.USER
            }
        )

        handlers_list.append(update_handler)
        handlers_list.append(config_info_handler)
        handlers_list.append(MessageHandler(filters.Regex(f"^{button_values['get_config_info']}$"), self.config_info))
        handlers_list.append(
            MessageHandler(filters.Regex(f"^{button_values['admin_panel']}$") & (self.admin_filter or None),
                           self.admin_panel))
        return handlers_list

    async def start_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[button_values['get_updated_config'], button_values['get_config_info']]]
        telegram_user: TelegramUser = update.api_kwargs['user_in_model']
        if telegram_user.telegram_is_staff:
            keyboard.append([button_values['admin_panel']])
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(
                message_values['start_menu_message'].format(full_name=telegram_user.get_telegram_full_name()),
                reply_markup=ReplyKeyboardMarkup(keyboard,
                                                 resize_keyboard=True))
        else:
            await update.message.reply_text(
                message_values['start_menu_message'].format(full_name=telegram_user.get_telegram_full_name()),
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return UserOrAdminEnum.USER

    async def get_client_with_config_uuid(self, message: str, telegram_user: TelegramUser):
        client_uuid = None
        client_name = None
        match = re.findall(r'vmess://[\w+\-=/]+', message)

        try:
            if match:
                config_link = match[0]
                config_base64 = config_link.removeprefix('vmess://')
                config_dict = json.loads(base64.urlsafe_b64decode(config_base64).decode())
                client_uuid = config_dict['id']
                config_number = re.search(r'^\d{4}', config_dict['ps'])
                if config_number:
                    client_name = f'{config_number}_Tel:@Sina8125'

            else:
                match = re.findall(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}',
                                   message)
                if match:
                    client_uuid = match[0]

        except Exception as e:
            print(e, file=open("tgbots/bots/bot.log", 'a+'))
            raise ValidationError('vmess link incorrect!', code=400)

        try:
            client, created = await Client.objects.aget_or_create(client_uuid=client_uuid,
                                                                  defaults={
                                                                      'client_name': client_name,
                                                                      'telegram_user': telegram_user})
            await client.telegram_users_using_config.aadd(telegram_user)
            await client.aget_update_client()
            return client
        except Exception as e:
            print(e, file=open("tgbots/bots/bot.log", 'a+'))
            raise ValidationError('client create or update error!', code=404)

    async def get_update_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[button_values['back_to_main_menu']]]
        await update.message.reply_text(message_values['send_config_for_update'],
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                         one_time_keyboard=True))
        return UserUpdatedConfig.SEND_CONFIG

    async def create_update_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            client: Client = await self.get_client_with_config_uuid(update.message.text,
                                                                    update.api_kwargs['user_in_model'])
        except ValidationError as e:
            if e.code == 400:
                await update.message.reply_text(message_values['vmess_or_uuid_error'])
                return await self.get_update_config(update, context)
            elif e.code == 404:
                await update.message.reply_text(message_values['config_not_found_or_error'])
            else:
                print(e, file=open("tgbots/bots/bot.log", 'a+'))
                await update.message.reply_text(message_values['problem_error'])
            return await self.start_menu(update, context)
        config1, config2 = client.connection_links
        response_message = message_values['config_update_message'].format(config1=config1, config2=config2,
                                                                          client_name=client.client_name.replace('_',
                                                                                                                 '\_'))
        await update.message.reply_text(response_message, parse_mode="Markdown")
        await self.start_menu(update, context)
        return UserOrAdminEnum.USER

    async def get_config_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[button_values['back_to_main_menu']]]
        await update.message.reply_text(message_values['send_config_to_get_info'],
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                         one_time_keyboard=True))
        return UserConfigInfo.SEND_CONFIG

    async def config_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            client: Client = await self.get_client_with_config_uuid(update.message.text,
                                                                    update.api_kwargs['user_in_model'])
        except ValidationError as e:
            if e.code == 400:
                await update.message.reply_text(message_values['vmess_or_uuid_error'])
                return await self.get_config_info(update, context)
            elif e.code == 404:
                await update.message.reply_text(message_values['config_not_found_or_error'])
            else:
                print(e, file=open("tgbots/bots/bot.log", 'a+'))
                await update.message.reply_text(message_values['problem_error'])
            return await self.start_menu(update, context)

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
                                  callback_data=str(UserConfigInfo.BACK_TO_MENU))]
        ]
        x = await update.message.reply_text('⏳')
        await asyncio.sleep(2)
        await x.delete()
        await update.message.reply_text(message_values['config_info_message'],
                                        reply_markup=InlineKeyboardMarkup(button))
        return UserConfigInfo.BACK_TO_MENU

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user: TelegramUser = update.api_kwargs['user_in_model']
        if not telegram_user.telegram_is_staff:
            await update.message.reply_text('حساب شما ادمین نیست!')
            return await self.start_menu(update, context)
        elif telegram_user.is_now_admin:
            await update.message.reply_text('الان ادمین هستی! یه دور استارت کن به نظرم')
            return await self.start_menu(update, context)
        telegram_user.is_now_admin = True
        await telegram_user.asave(update_fields=['is_now_admin'])
        return await self.start_menu(update, context)

    async def wrong_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(message_values['wrong_input_error'])
        return await self.start_menu(update, context)
