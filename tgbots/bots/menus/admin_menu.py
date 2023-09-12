from telegram import Update
from telegram.ext import ContextTypes


class AdminMenu:
    async def start_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('hi')
        pass
