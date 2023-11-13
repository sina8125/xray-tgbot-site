import asyncio
import base64
import json
import re
import jdatetime
from asgiref.sync import sync_to_async

from django.core.exceptions import ValidationError

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (ContextTypes, ConversationHandler, MessageHandler, filters, BaseHandler)

from .menu import Menu
from tgbots.models import TelegramUser
from xraypanels.models import Client
from ..enums import UserOrAdminEnum, UserEnum
from tgbots.bots.values import button_values, message_values


class UserMenu(Menu):

    def __init__(self, bot):
        super().__init__(bot)

    def handlers(self):
        handlers_list = [
            self.__update_config_handler(),
            self.__config_info_handler(),

            self.__admin_panel_handler()
        ]
        return handlers_list

    async def start_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[button_values['get_updated_config'], button_values['get_config_info']]]

        telegram_user: TelegramUser = update.api_kwargs['user_in_model']
        if telegram_user.telegram_is_staff:
            keyboard.append([button_values['admin_panel']])

        if update.callback_query:
            await update.callback_query.answer()
            if update.callback_query.data == str(UserOrAdminEnum.BACK_TO_MAIN_MENU.value):
                inline_keyboard = InlineKeyboardMarkup(self.remove_button(update.callback_query.data,
                                                                          update.callback_query.message.reply_markup.inline_keyboard))
                await update.callback_query.edit_message_reply_markup(inline_keyboard)

        await update.effective_chat.send_message(
            message_values['start_menu_message'].format(full_name=telegram_user.get_telegram_full_name()),
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return UserOrAdminEnum.USER.value

    # async def __get_client_with_config_uuid(self, message: str, telegram_user: TelegramUser):
    #     client_uuid = None
    #     try:
    #         match = re.findall(r'vmess://[\w+\-=/]+', message)
    #         if match:
    #             config_link = match[0]
    #             config_base64 = config_link.removeprefix('vmess://')
    #             config_dict = json.loads(base64.urlsafe_b64decode(config_base64).decode())
    #             client_uuid = config_dict['id']
    #             # config_number = re.match(r'^\d{4}', config_dict['ps'])
    #             # if config_number:
    #             #     client_name = f'{config_number.group(0)}_Tel:@Sina8125'
    #
    #         else:
    #             match = re.search(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}',
    #                               message)
    #             if match:
    #                 client_uuid = match.group(0)
    #     except Exception as e:
    #         print(e, file=open("tgbots/bots/bot.log", 'a+'))
    #         raise ValidationError('vmess link incorrect!', code=400)
    #
    #     try:
    #         client, created = await Client.aget_client_with_uuid(
    #             client_uuid=client_uuid,
    #             telegram_user=telegram_user
    #         )
    #         await client.telegram_users_using_config.aadd(telegram_user)
    #         return client
    #     except (ValidationError, Exception) as e:
    #         if isinstance(e, ValidationError):
    #             client_from_db = await sync_to_async(Client.objects.filter(client_uuid=client_uuid).last)()
    #             if client_from_db and not client_from_db.active:
    #                 return client_from_db
    #         # if created:
    #         #     await client.adelete()
    #         print(e, file=open("tgbots/bots/bot.log", 'a+'))
    #         raise ValidationError('client create or update error!', code=404)

    def __update_config_handler(self) -> BaseHandler:
        return ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex(f"^{button_values['get_updated_config']}$"), self.__get_update_config)
            ],
            states={
                UserEnum.SEND_CONFIG.value: [
                    MessageHandler(filters.Regex(r'vmess://[\w+\-=/]+'), self.__create_update_config),
                    MessageHandler(
                        filters.Regex(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'),
                        self.__create_update_config)
                ]},
            fallbacks=self.bot.fallback_handlers,
            map_to_parent={
                UserOrAdminEnum.USER.value: UserOrAdminEnum.USER.value
            },
            persistent=True,
            name='user_update_config_handler'
        )

    async def __get_update_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[button_values['back_to_main_menu']]]
        await update.message.reply_text(message_values['send_config_for_update'],
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return UserEnum.SEND_CONFIG.value

    async def __create_update_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            client: Client = await self._get_client_with_config_uuid(update.message.text,
                                                                     update.api_kwargs['user_in_model'])
        except ValidationError as e:
            return await self._get_client_exception_handler(e, update, context, self.__get_update_config)

        config1, config2 = client.connection_links
        if not config1:
            await update.message.reply_text(message_values['config_not_found_or_error'])
            return await super().start_menu(update, context)

        response_message = message_values['config_update_message'].format(config1=config1, config2=config2,
                                                                          client_name=client.client_name.replace('_',
                                                                                                                 '\_'))
        await update.message.reply_text(response_message, parse_mode="Markdown",
                                        reply_markup=ReplyKeyboardMarkup([[button_values['back_to_main_menu']]],
                                                                         resize_keyboard=True))
        return UserOrAdminEnum.USER.value
        # return await super().start_menu(update, context)

    def __config_info_handler(self) -> BaseHandler:
        return ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex(f"^{button_values['get_config_info']}$"), self.__get_config_info)
            ],
            states={
                UserEnum.SEND_CONFIG.value: [
                    MessageHandler(filters.Regex(r'vmess://[\w+\-=/]+'), self.__config_info),
                    MessageHandler(
                        filters.Regex(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'),
                        self.__config_info)
                ]
            },
            fallbacks=self.bot.fallback_handlers,
            map_to_parent={
                UserOrAdminEnum.USER.value: UserOrAdminEnum.USER.value
            },
            persistent=True,
            name='user_config_info_handler'
        )

    async def __get_config_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[button_values['back_to_main_menu']]]
        await update.message.reply_text(message_values['send_config_to_get_info'],
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return UserEnum.SEND_CONFIG.value

    async def __config_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        waiting_message = await update.message.reply_text('⏳')
        await asyncio.sleep(2)
        try:
            client: Client = await self._get_client_with_config_uuid(update.message.text,
                                                                     update.api_kwargs['user_in_model'])
        except ValidationError as e:
            await waiting_message.delete()
            return await self._get_client_exception_handler(e, update, context, self.__get_config_info)

        button = self._config_info_message_inline_keyboard(client)

        await waiting_message.delete()
        await update.message.reply_text(message_values['config_info_message'],
                                        reply_markup=InlineKeyboardMarkup(button))
        return UserOrAdminEnum.USER.value

    def __admin_panel_handler(self) -> BaseHandler:
        return MessageHandler(filters.Regex(f"^{button_values['admin_panel']}$") & (self.bot.admin_filter or None),
                              self.__admin_panel)

    async def __admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user: TelegramUser = update.api_kwargs['user_in_model']
        if not telegram_user.telegram_is_staff:
            await update.message.reply_text('حساب شما ادمین نیست!')
            return await super().start_menu(update, context)
        elif telegram_user.is_now_admin:
            await update.message.reply_text('الان ادمین هستی! یه دور استارت کن به نظرم')
            return await super().start_menu(update, context)
        telegram_user.is_now_admin = True
        await telegram_user.asave(update_fields=['is_now_admin'])
        return await super().start_menu(update, context)
