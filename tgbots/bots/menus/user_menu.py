from asgiref.sync import sync_to_async
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from django.contrib.auth.models import User

from ..enums import UserMenuEnum, UserOrAdminEnum, UserUpdatedConfig
from tgbots.models import TelegramUser
from ..values import button_values


class UserMenu:
    def user_handlers(self):
        handlers_list = list()

        update_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex(f"^{button_values['get_updated_config']}$"), self.get_update_config)],
            states={
                UserUpdatedConfig.SEND_CONFIG: [
                    MessageHandler(filters.Regex(r'vmess://[\w+\-=]+'), self.create_update_config)
                ]},
            fallbacks=[],
            map_to_parent={
                UserOrAdminEnum.USER: UserOrAdminEnum.USER
            }
        )
        handlers_list.append(update_handler)
        handlers_list.append(MessageHandler(filters.Regex(f"^{button_values['get_config_info']}$"), self.config_info))
        handlers_list.append(MessageHandler(filters.Regex(f"^{button_values['admin_panel']}$"), self.admin_panel))
        return handlers_list

    async def start_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # user: TelegramUser = update.message.from_user.api_kwargs['user_in_model']
        # await a.aupdate_last_message_time()
        # s = await sync_to_async(lambda: user.user.)()
        # print(s)
        keyboard = [[button_values['get_updated_config'], button_values['get_config_info']]]
        telegram_user: TelegramUser = update.message.from_user.api_kwargs['user_in_model']
        user = await sync_to_async(lambda: telegram_user.user)()
        if user and user.is_staff:
            keyboard.append([button_values['admin_panel']])
        # keyboard = InlineKeyboardMarkup(buttons, )

        # message = await update.message.reply_text('ملوباتم همیشه باهاتم',
        #                                           reply_markup=ReplyKeyboardMarkup(key, resize_keyboard=True,
        #                                                                            one_time_keyboard=True))
        # await update.message.edit_text(text='سلام', reply_markup=keyboard)
        # await message.edit_text('سلام ۲')
        # print(update.message.message_id)
        message = 'سلام به ربات '
        await update.message.reply_text('سلام', reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                                 one_time_keyboard=True))
        # await message.edit_reply_markup(keyboard)
        # await message.edit_reply_markup()
        return UserOrAdminEnum.USER

    async def get_update_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('hi', reply_markup=ReplyKeyboardRemove())
        return UserUpdatedConfig.SEND_CONFIG

    async def create_update_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print('2')
        await update.message.reply_text('2')
        await self.start_menu(update, context)
        return UserOrAdminEnum.USER

    async def config_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return UserOrAdminEnum.ADMIN

    async def hi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('خوبی؟')
        return UserMenuEnum.FIRST_MENU
