import os
import logging
from typing import List, Tuple, Dict
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler
)
from ultralytics import YOLO
# Настройка логирования 
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурационные параметры
TOKEN = "7513075860:AAGiLNS2XsWsDrQxVC8c8lIbSRX42FIwDTQ"
MODELS_DIR = f"{os.path.dirname(__file__)}\\models\\"  # Директория к моделям YOLO
MODEL_PATH = f"{MODELS_DIR}best.pt"  # Путь к модели YOLO
IMAGE_DIR = f"{os.path.dirname(__file__)}\\img\\"  # Директория для сохранения изображений
os.makedirs(MODELS_DIR, exist_ok=True) # Для хранения моделей YOLO
os.makedirs(IMAGE_DIR, exist_ok=True) # Для хранения загруженных изображений
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Состояния для ConversationHandler
SELECT_MODEL, SELECT_OUTPUT = range(2)

# Доступные модели
AVAILABLE_MODELS = {
    "best": "best.pt",
    "yolo11n": "yolo11n.pt",
}

# Варианты вывода
OUTPUT_OPTIONS = {
    "Фото": "photo",
    "Координаты объектов": "coords",
    "Количество объектов": "count",
    "Все данные": "all",
}

class BotConfig:
    """Класс для хранения настроек бота"""
    def __init__(self):
        self.model = None
        self.model_name = "best"
        self.output_format = "photo"

# Глобальная конфигурация
bot_config = BotConfig()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start - приветствие и инструкции."""
    reply_markup = ReplyKeyboardMarkup(
        [["/help"]],  # Кнопка с командой /help
        resize_keyboard=True,  # Автоматически подгонять размер кнопок
        one_time_keyboard=True  # Скрыть клавиатуру после нажатия
    )
    welcome_text = (
        "🚦 Добро пожаловать в бот для анализа дорожных ситуаций!\n\n"
        "📸 Пришлите фото дороги или парковки для анализа.\n"
        "Бот определит объекты и предоставит результаты детекции.\n\n"
        "⚠️ Отправляйте только четкие фотографии без искажений."
    )
    await update.message.reply_text(
        text=welcome_text,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    try: 
        help_text = (
            "ℹ️ Справка по использованию бота:\n\n"
            "/start - начать работу\n"
            "/help - эта справка\n"
            "/settings - настройки\n"
            "/current_settings - текущие настройки\n\n"
            "Отправьте фото для анализа дорожной ситуации."
        )
        
        await update.message.reply_text(help_text, reply_markup=ReplyKeyboardRemove())

    except Exception as e:
        logger.error(f"Ошибка в help_command: {e}")
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Не удалось отобразить справку"
            )
            
async def current_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /current_settings"""
    try:
        chat_id = update.message.chat.id
        settings_text = (
            "⚙️ Текущие настройки:\n\n"
            f"Модель: {bot_config.model_name if hasattr(bot_config, 'model_name') else 'Не выбрана'}\n"
            f"Формат вывода: {bot_config.output_format}\n"
        )
        await update.message.reply_text(
            text=settings_text,
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        logger.error(f"Ошибка в current_settings: {e}")
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Не удалось показать настройки"
            )

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /settings"""
    try:
        # Подготовка клавиатуры с моделями
        reply_keyboard = [list(AVAILABLE_MODELS.keys())]
        await update.message.reply_text(
            "⚙️ Выберите модель для анализа:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=reply_keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return SELECT_MODEL
    except Exception as e:
        logger.error(f"Ошибка в settings: {e}")
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Не удалось начать настройки"
            )
            return ConversationHandler.END


async def select_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора модели"""
    try:
        user_choice = update.message.text
        # Загрузка модели
        model_path = os.path.join(MODELS_DIR, AVAILABLE_MODELS[user_choice])
        try:
            bot_config.model = YOLO(model_path)
            bot_config.model_name = user_choice
            logger.info(f"Модель {model_path} успешно загружена")
            # Подготовка клавиатуры для выбора формата
            reply_keyboard = [list(OUTPUT_OPTIONS.keys())]
            markup = ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=True,
                resize_keyboard=True
            )
            # Отправка сообщения
            await update.message.reply_text(
                "✅ Модель успешно загружена\n"
                "📊 Выберите формат вывода результатов:",
                reply_markup=markup
            )
            return SELECT_OUTPUT
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            error_msg = "❌ Ошибка загрузки модели. Попробуйте еще раз."
            await update.message.reply_text(error_msg)
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Критическая ошибка в select_model: {e}")
        if update.effective_chat:
            await context.bot.send_message(
                text="❌ Произошла ошибка при выборе модели"
            )
        return ConversationHandler.END

async def select_output(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора формата вывода"""
    try:
        user_choice = update.message.text
        # Проверяем, что выбор пользователя допустим
        if user_choice not in OUTPUT_OPTIONS:
            await update.message.reply_text("Пожалуйста, выберите вариант из предложенных.")
            return SELECT_OUTPUT
        # Сохраняем выбранный формат
        bot_config.output_format = OUTPUT_OPTIONS[user_choice]
        context.user_data["output_format"] = user_choice
        # Отправляем подтверждение
        await update.message.reply_text(
            "✅ Настройки сохранены\n"
            "📸 Пришлите фото дороги или парковки для анализа.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка в select_output: {e}")
        # Безопасная отправка сообщения об ошибке
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Произошла ошибка при сохранении настроек"
            )
        return ConversationHandler.END

async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Корректный обработчик отмены настроек"""
    try:
        await update.message.reply_text(
            "Настройки отменены.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка в cancel_settings: {e}")
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Не удалось отменить настройки"
            )
        return ConversationHandler.END

async def process_image(file_path: str) -> Tuple[str, List]:
    """
    Обрабатывает изображение с помощью YOLO модели.
    
    Args:
        file_path: Путь к изображению для обработки
        
    Returns:
        Tuple: (путь к обработанному изображению, список результатов детекции)
        
    Raises:
        RuntimeError: Если не удалось загрузить модель или обработать изображение
    """
    try:
        if not bot_config.model:
            bot_config.model = YOLO(MODEL_PATH)
        results = bot_config.model.predict(file_path)
        
        # Сохранение результатов
        if bot_config.output_format in ("photo", "all"):
            output_path = f"{file_path}_result.jpg"
            results[0].save(filename=output_path)
            logger.debug(f"Сохранено обработанное изображение: {output_path}")
            
        # Подготовка данных для текстового файла
        if bot_config.output_format in ("count", "coords", "all"):
            result_data = [
                (int(box.cls.tolist()[0]), box.xywhn.tolist()[0])
                for result in results 
                for box in result.boxes
            ]
        
        return output_path, result_data
    except Exception as e:
        logger.error(f"Ошибка обработки изображения: {e}")
        return None

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик входящих фотографий."""
    try:
        user = update.message.from_user
        logger.info(f"Получено фото от пользователя {user.id} ({user.username})")
        # Скачивание фото
        photo_file = None
        if update.message.photo:
            # Если фото отправлено как изображение (сжатое)
            photo_file = await update.message.photo[-1].get_file()
        elif update.message.document and update.message.document.mime_type.startswith('image/'):
            # Если фото отправлено как файл
            if update.message.document.file_size > MAX_FILE_SIZE:
                await update.message.reply_text("Файл слишком большой (макс. 10МБ)")
                return
            photo_file = await update.message.document.get_file()
        else:
            await update.message.reply_text("Пожалуйста отправьте изображение")
            return
        file_path = os.path.join(IMAGE_DIR, f"{photo_file.file_id}.jpg")
        await photo_file.download_to_drive(file_path)
        
        # Уведомление пользователя о начале обработки
        await update.message.reply_text("🔄 Обрабатываю изображение...")
        
        # Обработка изображения
        result_path, result_data = await process_image(file_path)
        
        reply_markup = ReplyKeyboardMarkup(
                [["/help"], ["/settings"], ["/current_settings"]],
                one_time_keyboard=True,
                resize_keyboard=True)
        # Формирование текста результата
        caption_text = "✅ Результаты анализа изображения"
        if bot_config.output_format == "all":
            caption_text += f"\nКоличество объектов: {len(result_data)}"
                    
        # Отправка результата
        if bot_config.output_format in ["photo", "all"]:
            with open(result_path, "rb") as photo:
                await update.message.reply_photo(
                    photo, caption=caption_text,
                    reply_markup=reply_markup
                    )
        if bot_config.output_format == "count":
            await update.message.reply_text(
                f'✅ Результаты анализа изображения: {len(result_data)}',
                reply_markup=reply_markup
                )
        # Сохранение аннотаций
        if bot_config.output_format in ["coords", "all"] and result_data:
            annotation_path = f"{file_path}.txt"
            with open(annotation_path, "w") as f:
                for class_id, coords in result_data:
                    f.write(f"{class_id} {' '.join(map(str, coords))}\n")
            with open(annotation_path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    caption=f'{caption_text if bot_config.output_format == "coords" else ""}',
                    filename="coordinates.txt",
                    )
        logger.info(f"Обработка завершена для пользователя {user.id}")
    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке изображения. "
            "Попробуйте еще раз."
            )
 
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Улучшенный обработчик ошибок с проверкой всех случаев"""
    try:
        # Логируем ошибку
        error_msg = f"Ошибка в боте: {context.error}"
        logger.error(error_msg, exc_info=True)
        
        # Определяем куда отправлять сообщение об ошибке
        chat_id = None
        if update and update.effective_chat:
            chat_id = update.effective_chat.id
        elif update and update.callback_query and update.callback_query.message:
            chat_id = update.callback_query.message.chat.id
        
        # Если нашли chat_id, отправляем сообщение
        if chat_id:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже."
                )
            except Exception as send_error:
                logger.error(f"Ошибка при отправке сообщения об ошибке: {send_error}")
        
    except Exception as handler_error:
        logger.critical(f"Критическая ошибка в самом error_handler: {handler_error}")


def main() -> None:
    """Запуск бота."""
    # # Настройка ConversationHandler для меню настроек
    settings_handler = ConversationHandler(
        entry_points=[CommandHandler("settings", settings)],
        states={
            SELECT_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_model)],
            SELECT_OUTPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_output)],
        },
        fallbacks=[CommandHandler("cancel", cancel_settings)],
    )
    try:
        # Создание и настройка приложения
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Регистрация обработчиков
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(settings_handler)
        app.add_handler(CommandHandler("current_settings", current_settings))
        app.add_handler(MessageHandler(
            filters.PHOTO | 
            filters.Document.Category('image/')|
            (filters.TEXT & ~filters.COMMAND),
            handle_photo
        ))

        # Регистрация обработчика ошибок
        app.add_error_handler(error_handler)
        logger.info("Бот запущен...")
        app.run_polling()
        
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")


if __name__ == "__main__":
    main()