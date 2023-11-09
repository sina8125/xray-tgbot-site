from abc import ABC, abstractmethod

from django.core.exceptions import ValidationError
from telegram import Update
from telegram.ext import ContextTypes

from tgbots.bots.values import message_values
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
