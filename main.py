import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from db_utils import get_doctor_categories, execute_sql, add_user, get_doctors_by_category

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main_menu_keyboard():
    return ReplyKeyboardMarkup([["Поиск", "Отказаться от записи"]], resize_keyboard=True)

def start(update: Update, context: CallbackContext) -> None:
    try:
        chat_id = update.message.chat_id
        username = update.message.from_user.username
        add_user(chat_id, username)

        update.message.reply_text(
            'Привет! Я бот для записи к врачам. Нажми кнопку "Поиск" для возможности поиска талона для записи к врачу',
            reply_markup=main_menu_keyboard())
    except Exception as e:
        logger.error("An error occurred in the start function: %s", e)

def search(update: Update, context: CallbackContext) -> None:
    try:
        if update.message.text == "Поиск":
            categories = get_doctor_categories()

            if not categories:
                update.message.reply_text('Не найдено категорий врачей')
                return

            keyboard = [[category] for category in categories] + [["Назад"]]

            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            update.message.reply_text('Выберите категорию специалиста', reply_markup=reply_markup)
        elif update.message.text == "Назад":
            update.message.reply_text('Вы вернулись в главное меню', reply_markup=main_menu_keyboard())
        else:
            doctors = get_doctors_by_category(update.message.text)
            if not doctors:
                update.message.reply_text('Не найдено врачей в данной категории')
                return

            inline_keyboard = [[InlineKeyboardButton(f"{doctor['first_name']} {doctor['last_name']}",
                                                     callback_data=f"doctor_{doctor['id']}")] for doctor in doctors]
            reply_markup = InlineKeyboardMarkup(inline_keyboard)
            update.message.reply_text("Выберите врача:", reply_markup=reply_markup)

    except Exception as e:
        logger.error("An error occurred in the search function: %s", e)

def decline_appointment(update: Update, context: CallbackContext) -> None:
    try:
        update.message.reply_text('Вы отказались от записи', reply_markup=main_menu_keyboard())
    except Exception as e:
        logger.error("An error occurred in the decline_appointment function: %s", e)

def main() -> None:
    try:
        execute_sql()

        updater = Updater("6050183570:AAHMEeI293cB8dslPjD2M9Fq904TxV8zCoc", use_context=True)

        dispatcher = updater.dispatcher

        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, search))
        dispatcher.add_handler(MessageHandler(Filters.regex(r'^Отказаться от записи$'), decline_appointment))
        dispatcher.add_handler(CallbackQueryHandler(button))

        updater.start_polling()

        updater.idle()
    except Exception as e:
        logger.error("An error occurred in the main function: %s", e)

def button(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(text=f"Вы выбрали врача: {query.data.split('_')[1]}")

if __name__ == '__main__':
    main()
