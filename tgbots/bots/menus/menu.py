from abc import ABC, abstractmethod

import jdatetime
from django.core.exceptions import ValidationError
from telegram import Update, InlineKeyboardButton
from telegram.ext import ContextTypes

from tgbots.bots.enums import UserOrAdminEnum
from tgbots.bots.values import message_values, button_values
from tgbots.models import TelegramUser
from xraypanels.models import Client


class Menu(ABC):
    @abstractmethod
    def __init__(self, bot):
        self.bot = bot

    @abstractmethod
    async def start_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self.bot.start_menu(update, context)

    @abstractmethod
    def handlers(self):
        pass

    async def _get_client_with_config_uuid(self, message: str, telegram_user: TelegramUser = None):
        try:
            client_uuid = Client.export_uuid(message)
        except Exception as e:
            print(e, file=open("tgbots/bots/bot.log", 'a+'))
            raise ValidationError('vmess link incorrect!', code=400,
                                  params={'bot_message': message_values['vmess_or_uuid_error']})
        try:
            client, created = await Client.aget_client_with_uuid(
                client_uuid=client_uuid,
                telegram_user=telegram_user
            )
            return client
        except Exception as e:
            print(e, file=open("tgbots/bots/bot.log", 'a+'))
            raise ValidationError('client not found or error!', code=404)

    async def _get_client_with_config_name(self, message: str, telegram_user: TelegramUser = None):
        try:
            client_name = Client.export_name(message)
        except Exception as e:
            print(e, file=open("tgbots/bots/bot.log", 'a+'))
            raise ValidationError('client name incorrect!', code=400,
                                  params={'bot_message': message_values['client_name_or_number_error']})
        try:
            client, created = await Client.aget_client_with_client_name(
                client_name=client_name,
                telegram_user=telegram_user
            )
            return client
        except Exception as e:
            print(e, file=open("tgbots/bots/bot.log", 'a+'))
            raise ValidationError('client not found or error!', code=404)

    async def _get_client_exception_handler(self, exception: ValidationError, update: Update,
                                            context: ContextTypes.DEFAULT_TYPE, return_func=None):
        if exception.code == 400 and exception.params:
            await update.message.reply_text(exception.params['bot_message'])
            if return_func:
                return await return_func(update, context)
        elif exception.code == 404:
            await update.message.reply_text(message_values['config_not_found_or_error'])
        else:
            print(exception, file=open("tgbots/bots/bot.log", 'a+'))
            await update.message.reply_text(message_values['problem_error'])
        return await self.start_menu(update, context)

    async def wrong_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self.bot.wrong_input(update, context)

    def _config_info_message_inline_keyboard(self, client) -> list[[InlineKeyboardButton]]:
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

        temp_data = '-1'
        button = [
            [InlineKeyboardButton(text=client.client_name, callback_data=temp_data),
             InlineKeyboardButton(text='👤نام اشتراک', callback_data=temp_data)],
            [InlineKeyboardButton(text=client_status, callback_data=temp_data),
             InlineKeyboardButton(text='🔘وضعیت', callback_data=temp_data)],
            [InlineKeyboardButton(text=f'{client.get_total_upload[0]} {client.get_total_upload[1]}',
                                  callback_data=temp_data),
             InlineKeyboardButton(text='🔼آپلود', callback_data=temp_data)],
            [InlineKeyboardButton(text=f'{client.get_total_download[0]} {client.get_total_download[1]}',
                                  callback_data=temp_data),
             InlineKeyboardButton(text='🔽دانلود', callback_data=temp_data)],
            [InlineKeyboardButton(text=f'{client.get_total_usage[0]} {client.get_total_usage[1]}',
                                  callback_data=temp_data),
             InlineKeyboardButton(text='🔃حجم مصرفی', callback_data=temp_data)],
            [InlineKeyboardButton(
                text=total_flow,
                callback_data=temp_data),
                InlineKeyboardButton(text='🔄حجم کل', callback_data=temp_data)],
            [InlineKeyboardButton(
                text=total_remaining,
                callback_data=temp_data),
                InlineKeyboardButton(text='🔁حجم باقی مانده', callback_data=temp_data)],
            [InlineKeyboardButton(text=expire_time_ad, callback_data=temp_data),
             InlineKeyboardButton(text='📅تاریخ اتمام(میلادی)', callback_data=temp_data)],
            [InlineKeyboardButton(
                text=expire_time_solar,
                callback_data=temp_data),
                InlineKeyboardButton(text='📅تاریخ اتمام(شمسی)', callback_data=temp_data)],
            [InlineKeyboardButton(text=remaining_time if client.expire_time.timestamp() != 0 else 'نامحدود',
                                  callback_data=temp_data),
             InlineKeyboardButton(text='⏳زمان باقی مانده', callback_data=temp_data)],
            [InlineKeyboardButton(text=button_values['back_to_main_menu'],
                                  callback_data=str(UserOrAdminEnum.BACK_TO_MAIN_MENU.value))]
        ]
        return button

    @staticmethod
    def remove_button(button_data, keyboard):
        updated_keyboard = []

        for row in keyboard:
            updated_row = []
            for button in row:
                if button.callback_data != button_data:
                    updated_row.append(button)
            if updated_row:
                updated_keyboard.append(updated_row)

        return updated_keyboard
