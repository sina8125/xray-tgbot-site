from typing import Final
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import ReplyKeyboardMarkup, Update, Bot
import base64
import json
import re
import sys
from dateutil.relativedelta import relativedelta
from datetime import datetime
import jdatetime
import pytz
import random

TOKEN: Final = "5976056923:AAF5UCAnNTg19EOqtJOvVdgSVBj_o-bwhKA"
ADMIN: Final = 179102335
USER_FILE: Final = "/home/sina/users.txt"
FORMAT_FILE: Final = "/home/sina/format.txt"
NEW_FILE: Final = "/root/new.txt"
PROXY: Final = "http://127.0.0.1:2081"
HEADER: list = ["telewebion.com", "zula.ir"]


####################################################


def get_config_info(message: str):
    message = message.removeprefix('vmess://')
    message = base64.urlsafe_b64decode(message).decode()
    message = json.loads(message)
    output = {"id": message["id"],
              "port": message["port"], "ps": message["ps"]}
    return output


def get_vmess_link(config_info, adress, host, operator):
    vmess_config = {
        "add": f"{adress}.sinarahimi.tk",
        "aid": "0",
        "alpn": "",
        "fp": "",
        "host": f"{host}",
        "id": f"{config_info['id']}",
        "net": "tcp",
        "path": "/",
        "port": f"{config_info['port']}",
        "ps": f"{config_info['ps']}_Tel:@Sina8125 {operator}",
        "scy": "auto",
        "sni": "",
        "tls": "",
        "type": "http",
        "v": "2"
    }
    # Convert JSON object to base64-encoded string
    vmess_base64 = base64.urlsafe_b64encode(
        json.dumps(vmess_config).encode()).decode()

    # Construct VMess link with base64-encoded string
    vmess_link = f"vmess://{vmess_base64}"
    return vmess_link


def create_config(config_info):
    header1 = "telewebion.com"
    header2 = "zula.ir"
    global HEADER
    if len(HEADER) >= 2 and not HEADER == [header1, header2]:
        header1, header2 = random.sample(HEADER, 2)
    config1 = get_vmess_link(
        config_info, "mci", header1, "(Hamrah Aval)")
    config2 = get_vmess_link(
        config_info, "mtn", header2, "(Irancell)")
    return config1, config2


def update_config(message):
    try:
        with open(FORMAT_FILE, 'r', encoding="utf_8") as file:
            fileData = file.read()

        config_info = get_config_info(message)
        config_info['ps'] = re.search("^\d{4}", config_info['ps']).group(0)
        config1, config2 = create_config(config_info)
        fileData = fileData.replace('number', config_info['ps'])
        fileData = fileData.replace('config1', config1)
        fileData = fileData.replace('config2', config2)
        return fileData
    except Exception as x:
        print(x)
        return


def find_matches(info_dict: dict, number: str) -> list:
    for k in info_dict:
        if re.match(k, number):
            return info_dict[k]


def create_new_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = {10: 40, 20: 70, 30: 90, 50: 115, 100: 200, 150: 270, 200: 320}

        with open(NEW_FILE, 'r', encoding="utf_8") as file:
            fileData = file.read()

        uuid = context.args[0]
        number = context.args[1]
        total_flow = int(context.args[2])
        ip_limit = int(context.args[3]) if len(context.args) > 3 else 1

        gregorian_date = datetime.now(tz=pytz.timezone(
            'Asia/Tehran')) + relativedelta(days=30)
        jalali_date = jdatetime.datetime.fromgregorian(datetime=gregorian_date)

        price = context.args[4] if len(context.args) > 4 else str(price[total_flow] + ((ip_limit - 1) * 25))

        info_dict = {"^11.*": 2053, "^12.*": 2083,
                     "^13.*": 2087, "^14.*": 2096, "^15.*": 8443}
        config_info = {"id": uuid, "port": find_matches(
            info_dict, number), "ps": number}
        config1, config2 = create_config(config_info)
        fileData = fileData.replace('number', number)
        fileData = fileData.replace('config1', config1)
        fileData = fileData.replace('config2', config2)
        fileData = fileData.replace(
            'Gregorian_DATE', (gregorian_date.strftime("%Y/%m/%d")))
        fileData = fileData.replace(
            'JALALI_DATE', (jalali_date.strftime("%Y/%m/%d")))
        fileData = fileData.replace('total_flow', str(total_flow))
        fileData = fileData.replace('ip_limit', str(ip_limit))
        fileData = fileData.replace('price', price)
        return fileData
    except IndexError as i:
        return "تعداد آرگومان ها غیر مجاز"
    except Exception as e:
        print(e, file=sys.stderr)
        return "خطا"


####################################################


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [["دریافت کانفیگ جدید"]]
    message = "جهت دریافت کانفیگ جدید، گزینه دریافت کانفیگ را بزنید و کانفیگ خود را ارسال کنید"

    await update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True,
                                                                              one_time_keyboard=True))


def check_user_availble(user_file, user_id):
    for i in user_file:
        if user_id in i:
            return True
    return False


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = "به ربات دریافت کانفیگ خوش آمدید\nاین ربات جهت بروزرسانی کانفیگ ایجاد شده\nدر صورت بروز مشکل با پشتیبانی در ارتباط باشید\n@Sina8125"
    with open(USER_FILE, 'w+') as file:
        if not check_user_availble(file, str(update.message.chat_id)):
            file.write(str(update.message.chat_id))
            file.write('\n')
    await update.message.reply_text(message)
    await main_menu(update, context)


async def update_header(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global HEADER
    if context.args and (context.args[0] == "*" or context.args[0] == "**"):
        if context.args[0] == "*":
            HEADER += context.args[1:]
        else:
            HEADER = HEADER[0:2]
    else:
        HEADER = context.args
    await update.message.reply_text(f'هدر ها آپدیت شد!\n{HEADER}')


async def new_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(create_new_config(update, context), parse_mode="Markdown")


async def message_hendler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "دریافت کانفیگ جدید" in update.message.text:
        await update.message.reply_text(
            "یکی از کانفیگ های خود را که هنگام خرید به شما داده شده است(همراه اول یا ایرانسل) بدون هیچ متن اضافه ارسال کنید\n\nمثال👇:")
        await update.message.reply_text(
            "vmess://eyJhZGQiOiAiIiwgImFpZCI6ICIwIiwgImFscG4iOiAiIiwgImZwIjogIiIsICJob3N0IjogIiIsICJpZCI6ICIiLCAibmV0IjogIndzIiwgInBhdGgiOiAiL1RlbDpAU2luYTgxMjUiLCAicG9ydCI6ICIiLCAicHMiOiAiIiwgInNjeSI6ICJhdXRvIiwgInNuaSI6ICIiLCAidGxzIjogInRscyIsICJ0eXBlIjogIiIsICJ2IjogIjIifQ==")
        return

    elif update.message.text.startswith('vmess://'):
        config = update_config(update.message.text)
        if config:
            await update.message.reply_text(config, parse_mode="Markdown")
            await main_menu(update, context)
            return
    print(update.message.text, file=sys.stderr)
    username = f'@{update.message.chat.username}'
    await context.bot.send_message(chat_id=ADMIN,
                                   text=f'پیام از {username if update.message.chat.username else update.message.chat.full_name}:\n{update.message.text}')
    await context.bot.forward_message(chat_id=ADMIN, from_chat_id=update.message.chat.id,
                                      message_id=update.message.message_id)
    await update.message.reply_text(
        "کانفیگ به درستی پذیرش نشد\nلطفا مجدد ارسال کنید\nدر صورتی که مشکل حل نشد به آی دی زیر پیام بدید\n@Sina8125")
    await main_menu(update, context)


async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(USER_FILE, 'r') as file:
        for user_id in file:
            try:
                await context.bot.send_message(chat_id=user_id, text=re.sub("([^\s]+)\s", "", update.message.text, 1))
            except Exception as e:
                print(e, file=sys.stderr)
                await context.bot.send_message(chat_id=ADMIN, text=f'خطا در ارسال پیام به {user_id}')


app = Application.builder().token(TOKEN).proxy_url(PROXY).get_updates_proxy_url(PROXY).build()
app.add_handler(CommandHandler("start", start_handler))
app.add_handler(CommandHandler('send', send, filters=filters.User(ADMIN)))
app.add_handler(CommandHandler(
    "new", new_config, filters=filters.User(ADMIN)))
app.add_handler(CommandHandler(
    "header", update_header, filters=filters.User(ADMIN)))
app.add_handler(MessageHandler(filters.TEXT, message_hendler))
# app.run_polling()
