import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler, \
    ConversationHandler
from db_utils import get_doctor_categories, execute_sql, add_user, get_hospitals_by_category, \
    get_doctors_by_category_and_hospital, get_doctor_info, get_hospital_info, add_appointment, get_user_id_by_chat_id, \
    get_booked_hours, get_user_appointments_info, cancel_appointment_by_id, get_appointment_info, add_search_request, \
    user_exists
import datetime
import holidays

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

FIRST_NAME, LAST_NAME, PATRONYMIC, MEDICAL_POLICY, PASSPORT = range(5)

def main_menu_keyboard():
    icons = ["🔍"]  # Значки для кнопок "Поиск" и "Отказаться от записи"
    keyboard = [[f"{icons[0]} Поиск", f" Мои активные записи"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def category_menu_keyboard(categories):
    return ReplyKeyboardMarkup([[category] for category in categories] + [["Назад"]], resize_keyboard=True)


def start(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat_id

    if user_exists(chat_id):
        update.message.reply_text(
            'Регистрация уже завершена. Нажмите кнопку "Поиск" для возможности поиска талона для записи к врачу.',
            reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END
    else:
        update.message.reply_text('Привет! Я бот для записи к врачам. Пожалуйста, введите ваше имя:')
        return FIRST_NAME



def get_first_name(update: Update, context: CallbackContext) -> int:
    context.user_data['first_name'] = update.message.text
    update.message.reply_text('Введите вашу фамилию:')
    return LAST_NAME


def get_last_name(update: Update, context: CallbackContext) -> int:
    context.user_data['last_name'] = update.message.text
    update.message.reply_text('Введите ваше отчество:')
    return PATRONYMIC


def get_patronymic(update: Update, context: CallbackContext) -> int:
    context.user_data['patronymic'] = update.message.text
    update.message.reply_text('Введите ваш медицинский полис:')
    return MEDICAL_POLICY


def get_medical_policy(update: Update, context: CallbackContext) -> int:
    context.user_data['medical_policy'] = update.message.text
    update.message.reply_text('Введите ваш паспорт:')
    return PASSPORT


def get_passport(update: Update, context: CallbackContext) -> int:
    context.user_data['passport'] = update.message.text
    chat_id = update.message.chat_id
    username = update.message.from_user.username
    first_name = context.user_data['first_name']
    last_name = context.user_data['last_name']
    patronymic = context.user_data['patronymic']
    medical_policy = context.user_data['medical_policy']
    passport = context.user_data['passport']

    add_user(chat_id, username, first_name, last_name, patronymic, medical_policy, passport)

    update.message.reply_text(
        'Регистрация завершена! Нажми кнопку "Поиск" для возможности поиска талона для записи к врачу',
        reply_markup=main_menu_keyboard())
    return ConversationHandler.END
def search(update: Update, context: CallbackContext) -> None:
    try:
        if update.message.text == "🔍 Поиск":
            categories = get_doctor_categories()

            if not categories:
                update.message.reply_text('Не найдено категорий врачей')
                return

            update.message.reply_text('Выберите категорию специалиста', reply_markup=category_menu_keyboard(categories))
        elif update.message.text == "Назад":
            update.message.reply_text('Вы вернулись в главное меню', reply_markup=main_menu_keyboard())
        elif update.message.text == "Мои активные записи":
            # Handle "Мои активные записи" button press
            chat_id = update.message.chat_id
            user_id = get_user_id_by_chat_id(chat_id)
            if user_id:
                appointments_info = get_user_appointments_info(user_id)
                if appointments_info:
                    for appointment_info in appointments_info:
                        appointment_id, first_name, last_name, hospital_name, hospital_address, appointment_date = appointment_info
                        message_text = f"Врач: {first_name} {last_name}, Место: {hospital_name}, Адрес: {hospital_address}, Время: {appointment_date}"
                        inline_keyboard = [
                            [InlineKeyboardButton("Отменить запись", callback_data=f"cancel_{appointment_id}")]]
                        reply_markup = InlineKeyboardMarkup(inline_keyboard)
                        update.message.reply_text(message_text, reply_markup=reply_markup)
                else:
                    update.message.reply_text("У вас нет активных записей.")
            else:
                update.message.reply_text("У вас нет активных записей.")
        else:
            hospitals = get_hospitals_by_category(update.message.text)
            if not hospitals:
                update.message.reply_text('К сожалению, не нашлось медицинских учреждений с врачами выбранной вами '
                                          'категории')
                return

            # Сохраняем выбранную категорию в контексте пользователя
            context.user_data['selected_category'] = update.message.text

            inline_keyboard = [[InlineKeyboardButton(hospital['name'], callback_data=f"hospital_{hospital['id']}")] for
                               hospital in hospitals]
            reply_markup = InlineKeyboardMarkup(inline_keyboard)
            update.message.reply_text(
                "Нашлось несколько медицинских учреждений, в которых есть врачи нужной вам категории. Выберите более удобное место для посещения:",
                reply_markup=reply_markup)

    except Exception as e:
        logger.error("An error occurred in the search function: %s", e)


def cancel_appointment(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query
        query.answer()

        # Получаем ID записи из данных колбэка
        appointment_id = query.data.split('_')[1]

        # Получаем информацию о записи
        appointment_info = get_appointment_info(appointment_id)

        if not appointment_info:
            query.edit_message_text("Ошибка при получении информации о записи.")
            return

        # Извлекаем данные о записи
        doctor_name = appointment_info['doctor_name']
        appointment_date = appointment_info['appointment_date']

        # Формируем сообщение с подтверждением отмены записи
        message_text = f"Вы уверены, что хотите отменить запись к врачу {doctor_name} на {appointment_date}?"

        # Создаем инлайн клавиатуру с кнопками "Да" и "Нет"
        inline_keyboard = [
            [InlineKeyboardButton("Да", callback_data=f"confirm_cancel_{appointment_id}"),
             InlineKeyboardButton("Нет", callback_data=f"rollback")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)

        # Отправляем сообщение с подтверждением отмены записи
        query.edit_message_text(message_text, reply_markup=reply_markup)
    except Exception as e:
        logger.error("An error occurred in the cancel_appointment function: %s", e)


def confirm_cancel_appointment(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query
        query.answer()

        # Получаем ID записи из данных колбэка
        appointment_id = query.data.split('_')[2]

        # Отменяем запись
        cancel_appointment_by_id(appointment_id)

        # Отправляем сообщение об успешной отмене записи
        query.edit_message_text("Запись успешно отменена.")
    except Exception as e:
        logger.error("An error occurred in the confirm_cancel_appointment function: %s", e)


def cancel_cancel_operation(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query
        query.answer()

        # Отправляем сообщение о том, что отмена записи отменена
        query.edit_message_text("Действие отменено.")
    except Exception as e:
        logger.error("An error occurred in the cancel_cancel_operation function: %s", e)


def confirm_appointment(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query
        query.answer()
        selected_time = query.data.split('_')[2]  # Время в формате 'HH:MM'
        selected_date = query.data.split('_')[1]  # Дата в формате 'YYYY-MM-DD'

        doctor_id = context.user_data.get('selected_doctor')
        hospital_id = context.user_data.get('selected_hospital')
        chat_id = update.effective_user.id
        # Получаем информацию о враче и больнице
        doctor_info = get_doctor_info(doctor_id)
        hospital_info = get_hospital_info(hospital_id)

        if doctor_info is None or hospital_info is None:
            query.edit_message_text("Произошла ошибка. Попробуйте снова.")
            return

        message_text = f"Вы уверены, что хотите записаться к врачу {doctor_info['first_name']} {doctor_info['last_name']} " \
                       f"в больницу {hospital_info['name']} на {selected_time}?"

        # Создаем инлайн клавиатуру с кнопками "Да" и "Нет"
        inline_keyboard = [
            [InlineKeyboardButton("Да", callback_data=f"confirm_appointment_{selected_date}_{selected_time}"),
             InlineKeyboardButton("Нет", callback_data=f"rollback")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)

        query.edit_message_text(message_text, reply_markup=reply_markup)
    except Exception as e:
        logger.error("An error occurred in the confirm_appointment function: %s", e)


def confirm_appointment_addition(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query
        query.answer()
        selected_date = query.data.split('_')[2]  # Дата в формате 'YYYY-MM-DD'
        selected_time = query.data.split('_')[3]  # Время в формате 'HH:MM'

        time_obj = datetime.datetime.strptime(selected_time, '%H:%M').time()

        date_obj = datetime.datetime.strptime(selected_date, '%Y-%m-%d').date()
        appointment_datetime = datetime.datetime.combine(date_obj, time_obj)

        doctor_id = context.user_data.get('selected_doctor')
        hospital_id = context.user_data.get('selected_hospital')
        chat_id = update.effective_user.id
        user_id = get_user_id_by_chat_id(chat_id)  # Получаем id пользователя из базы данных

        # Добавляем запись о записи на прием к врачу в базу данных
        add_appointment(user_id, doctor_id, appointment_datetime)

        # Получаем информацию о враче и больнице
        doctor_info = get_doctor_info(doctor_id)
        hospital_info = get_hospital_info(hospital_id)

        if doctor_info is None or hospital_info is None:
            query.edit_message_text("Произошла ошибка при добавлении записи. Попробуйте снова.")
            return

        query.edit_message_text(
            f"Вы успешно записаны к врачу {doctor_info['first_name']} {doctor_info['last_name']} "
            f"в больницу {hospital_info['name']} на {selected_time}."
        )

        # Очищаем данные из контекста пользователя
        context.user_data.pop('selected_doctor', None)
        context.user_data.pop('selected_hospital', None)
        context.user_data.pop('selected_category', None)

    except Exception as e:
        logger.error("An error occurred in the confirm_appointment_addition function: %s", e)


def doctor_selected_hour(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        query.answer()

        # Получаем выбранную дату из данных колбэка
        selected_date = query.data.split('_')[1]
        selected_date = datetime.datetime.strptime(selected_date, '%Y-%m-%d').date()

        # Получаем список доступных часов для записи (с 9:00 до 14:00)
        available_hours = [datetime.time(hour) for hour in range(9, 15)]

        # Получаем часы, для которых уже есть записи в базе данных для выбранной даты
        booked_hours = get_booked_hours(selected_date, doctor_id=context.user_data.get('selected_doctor'))

        # Исключаем из списка доступных часов те, для которых уже есть записи
        available_hours = [hour for hour in available_hours if hour not in booked_hours]

        # Создаем инлайн клавиатуру с кнопками для каждого доступного часа
        inline_keyboard = [[InlineKeyboardButton(hour.strftime('%H:%M'),
                                                 callback_data=f"time_{selected_date}_{hour.strftime('%H:%M')}")] for
                           hour in available_hours]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)

        query.edit_message_text(f"Выберите время для посещения врача {selected_date.strftime('%d %B')}:",
                                reply_markup=reply_markup)
    except Exception as e:
        logger.error("An error occurred in the doctor_selected_hour function: %s", e)


def doctor_selected_day(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        query.answer()

        selected_doctor_id = query.data.split('_')[1]
        context.user_data['selected_doctor'] = selected_doctor_id

        # Получаем список ближайших 14 дней от текущей даты
        today = datetime.date.today()
        dates = [today + datetime.timedelta(days=i) for i in range(14)]

        # Определяем праздничные дни для вашего региона
        my_holidays = holidays.Russia()
        workdays = [date for date in dates if date.weekday() < 5 and date not in my_holidays]

        # Создаем инлайн клавиатуру с кнопками для каждой доступной даты
        inline_keyboard = []
        for date in workdays:
            # Получаем список забронированных часов для данного дня и выбранного врача
            booked_hours = get_booked_hours(date, doctor_id=selected_doctor_id)

            # Если все часы забронированы, добавляем кнопку с уведомлением
            if len(booked_hours) == 6:
                continue
                #inline_keyboard.append([InlineKeyboardButton(date.strftime('%d %B (нет свободных талонов)'),
                #                                             callback_data=f"notify_{date.strftime('%Y-%m-%d')}")])
            else:
                inline_keyboard.append([InlineKeyboardButton(date.strftime('%d %B'),
                                                             callback_data=f"day_{date.strftime('%Y-%m-%d')}")])

        reply_markup = InlineKeyboardMarkup(inline_keyboard)

        query.edit_message_text("Выберите дату для посещения врача:", reply_markup=reply_markup)
    except Exception as e:
        logger.error("An error occurred in the doctor_selected_day function: %s", e)
        raise e


def notify_selected_day(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        query.answer()

        selected_date = query.data.split('_')[1]
        selected_date = datetime.datetime.strptime(selected_date, '%Y-%m-%d').date()

        doctor_info = get_doctor_info(context.user_data.get('selected_doctor'))

        # Создаем инлайн клавиатуру с кнопками "Искать" и "Назад"
        inline_keyboard = [
            [InlineKeyboardButton("Искать", callback_data=f"search_{selected_date.strftime('%Y-%m-%d')}"),
             InlineKeyboardButton("Назад", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)

        query.edit_message_text(
            f"Сейчас на {selected_date.strftime('%d %B')} для {doctor_info['first_name']} {doctor_info['last_name']} нет свободных талонов, но они еще могут появиться, если вы нажмете кнопку \"Искать\", то я начну проверять наличие свободных талонов на эту дату каждые 2 минуты и обязательно сообщу вам, когда они появятся!",
            reply_markup=reply_markup)
    except Exception as e:
        logger.error("An error occurred in the notify_selected_day function: %s", e)
        raise e


def search_for_available_slots(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        query.answer()

        selected_date = query.data.split('_')[1]  # Extract the selected date from the callback data
        selected_date = datetime.datetime.strptime(selected_date, '%Y-%m-%d').date()

        doctor_id = context.user_data.get('selected_doctor')
        chat_id = update.effective_user.id
        user_id = get_user_id_by_chat_id(chat_id)

        # Insert a new record into the search_requests table
        add_search_request(user_id, doctor_id, selected_date)

        query.edit_message_text("Поиск свободных талонов начат. Я буду сообщать вам о результате.")

    except Exception as e:
        logger.error("An error occurred in the search_for_available_slots function: %s", e)


def button(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        query.answer()

        # Получаем ID больницы из данных колбэка
        hospital_id = query.data.split('_')[1]
        context.user_data['selected_hospital'] = hospital_id
        # Получаем выбранную категорию из контекста пользователя
        selected_category = context.user_data.get('selected_category')

        # Получаем врачей нужной категории в этой больнице
        doctors = get_doctors_by_category_and_hospital(selected_category, hospital_id)

        if not doctors:
            query.edit_message_text("В данной больнице нет врачей выбранной категории.")
            return

        # Создаем список кнопок для каждого врача
        inline_keyboard = [[InlineKeyboardButton(f"{doctor['first_name']} {doctor['last_name']}",
                                                 callback_data=f"doctor_{doctor['id']}")] for doctor in doctors]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)

        query.edit_message_text("Выберите врача:", reply_markup=reply_markup)
    except Exception as e:
        logger.error("An error occurred in the button function: %s", e)


def main() -> None:
    try:
        execute_sql()

        updater = Updater("6050183570:AAHMEeI293cB8dslPjD2M9Fq904TxV8zCoc", use_context=True)

        dispatcher = updater.dispatcher

        # Conversation handler for registration
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                FIRST_NAME: [MessageHandler(Filters.text & ~Filters.command, get_first_name)],
                LAST_NAME: [MessageHandler(Filters.text & ~Filters.command, get_last_name)],
                PATRONYMIC: [MessageHandler(Filters.text & ~Filters.command, get_patronymic)],
                MEDICAL_POLICY: [MessageHandler(Filters.text & ~Filters.command, get_medical_policy)],
                PASSPORT: [MessageHandler(Filters.text & ~Filters.command, get_passport)],
            },
            fallbacks=[CommandHandler('cancel', cancel_cancel_operation)],
        )

        dispatcher.add_handler(conv_handler)

        # Add existing handlers
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, search))
        dispatcher.add_handler(CallbackQueryHandler(button, pattern="hospital_"))
        dispatcher.add_handler(CallbackQueryHandler(doctor_selected_day, pattern=r'^doctor_'))
        dispatcher.add_handler(CallbackQueryHandler(doctor_selected_hour, pattern=r'^day_'))
        dispatcher.add_handler(CallbackQueryHandler(confirm_appointment, pattern=r'^time_'))
        dispatcher.add_handler(CallbackQueryHandler(cancel_appointment, pattern=r'^cancel_'))
        dispatcher.add_handler(CallbackQueryHandler(confirm_cancel_appointment, pattern=r'^confirm_cancel_'))
        dispatcher.add_handler(CallbackQueryHandler(cancel_cancel_operation, pattern=r'^rollback'))
        dispatcher.add_handler(CallbackQueryHandler(confirm_appointment_addition, pattern=r'^confirm_appointment'))
        dispatcher.add_handler(CallbackQueryHandler(notify_selected_day, pattern=r'^notify'))
        dispatcher.add_handler(CallbackQueryHandler(search_for_available_slots, pattern=r'^search_'))

        updater.start_polling()
        updater.idle()

    except Exception as e:
        logger.error("An error occurred in the main function: %s", e)


if __name__ == '__main__':
    main()
