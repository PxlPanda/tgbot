import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import json
import os
from datetime import datetime
import pytz
import sys
import tempfile
import atexit

# Константы для состояний
WAITING_FOR_TASK = 1
WAITING_FOR_SCHEDULE_MESSAGE = 2
WAITING_FOR_SCHEDULE_TIME = 3

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация бота
BOT_CONFIG = {
    'admin_id': None,
    'player_id': None,
    'scheduled_messages': []
}

class SingleInstance:
    def __init__(self):
        self.lockfile = os.path.join(tempfile.gettempdir(), 'quest_bot.lock')
        self.cleanup_lock()
        
        try:
            if os.path.exists(self.lockfile):
                # Проверяем, не устарел ли файл блокировки (больше 1 часа)
                if os.path.getmtime(self.lockfile) < datetime.now().timestamp() - 3600:
                    os.remove(self.lockfile)
                else:
                    # Проверяем, жив ли процесс
                    with open(self.lockfile, 'r') as f:
                        old_pid = int(f.read().strip())
                    if self.is_process_running(old_pid):
                        print("Another instance is already running. Exiting.")
                        sys.exit(1)
                    else:
                        os.remove(self.lockfile)
            
            with open(self.lockfile, 'w') as f:
                f.write(str(os.getpid()))
            
            atexit.register(self.cleanup_lock)
            
        except Exception as e:
            print(f"Error creating lock file: {e}")
            sys.exit(1)
    
    def cleanup_lock(self):
        try:
            if os.path.exists(self.lockfile):
                os.remove(self.lockfile)
        except:
            pass
    
    def is_process_running(self, pid):
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

class QuestBot:
    _instance = None
    _scheduled_messages = BOT_CONFIG['scheduled_messages']
    _player_id = BOT_CONFIG['player_id']
    _admin_id = BOT_CONFIG['admin_id']

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QuestBot, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        pass

    @property
    def admin_id(self):
        return self._admin_id

    @property
    def player_id(self):
        return self._player_id

    @player_id.setter
    def player_id(self, value):
        self._player_id = value
        BOT_CONFIG['player_id'] = value

    @property
    def scheduled_messages(self):
        return self._scheduled_messages

    def start(self, update: Update, context: CallbackContext) -> None:
        user_id = update.effective_user.id
        
        if user_id == self.admin_id:
            update.message.reply_text("Вы администратор квеста. Используйте /help для просмотра команд.")
        elif not self.player_id:
            self.player_id = user_id
            update.message.reply_text("Добро пожаловать в квест! Ждите задание от хозяина игры.")
            context.bot.send_message(
                self.admin_id,
                f"Игрок присоединился к квесту! Используйте /send_task для отправки задания."
            )
        elif user_id == self.player_id:
            update.message.reply_text("Добро пожаловать обратно в квест!")
        else:
            update.message.reply_text("Извините, этот бот предназначен только для одного игрока.")

    def help_command(self, update: Update, context: CallbackContext) -> None:
        user_id = update.effective_user.id
        
        if user_id == self.admin_id:
            help_text = """
Доступные команды:
/send_task - Отправить новое задание игроку
/schedule_message - Запланировать сообщение на определенное время
/list_scheduled - Показать список запланированных сообщений
/cancel_scheduled <id> - Отменить запланированное сообщение
/help - Показать это сообщение
            """
            update.message.reply_text(help_text)
        else:
            update.message.reply_text("Ждите заданий от администратора!")

    def send_task(self, update: Update, context: CallbackContext) -> int:
        if update.effective_user.id != self.admin_id:
            return ConversationHandler.END
        
        update.message.reply_text("Введите текст задания:")
        return WAITING_FOR_TASK

    def process_task(self, update: Update, context: CallbackContext) -> int:
        if update.effective_user.id != self.admin_id:
            return ConversationHandler.END

        task_text = update.message.text
        if self.player_id:
            context.bot.send_message(self.player_id, f"Новое задание:\n{task_text}")
            update.message.reply_text("Задание отправлено игроку!")
        else:
            update.message.reply_text("Игрок еще не присоединился к квесту!")
        return ConversationHandler.END

    def schedule_message(self, update: Update, context: CallbackContext) -> int:
        if update.effective_user.id != self.admin_id:
            return ConversationHandler.END
        
        update.message.reply_text("Введите текст сообщения, которое нужно запланировать:")
        return WAITING_FOR_SCHEDULE_MESSAGE

    def save_scheduled_message(self, update: Update, context: CallbackContext) -> int:
        if update.effective_user.id != self.admin_id:
            return ConversationHandler.END

        context.user_data['scheduled_message_text'] = update.message.text
        update.message.reply_text(
            "Введите время отправки в формате 'ГГГГ-ММ-ДД ЧЧ:ММ'\n"
            "Например: 2024-12-25 15:30"
        )
        return WAITING_FOR_SCHEDULE_TIME

    def process_schedule_time(self, update: Update, context: CallbackContext) -> int:
        if update.effective_user.id != self.admin_id:
            return ConversationHandler.END

        try:
            # Парсим время
            schedule_time = datetime.strptime(update.message.text, '%Y-%m-%d %H:%M')
            # Устанавливаем московское время
            moscow_tz = pytz.timezone('Europe/Moscow')
            schedule_time = moscow_tz.localize(schedule_time)

            # Создаем новое запланированное сообщение
            message_id = len(self.scheduled_messages)
            scheduled_message = {
                'id': message_id,
                'text': context.user_data['scheduled_message_text'],
                'time': schedule_time.isoformat(),
                'sent': False
            }
            
            self.scheduled_messages.append(scheduled_message)
            BOT_CONFIG['scheduled_messages'] = self.scheduled_messages

            # Планируем отправку сообщения
            context.job_queue.run_once(
                self.send_scheduled_message,
                when=schedule_time,
                context={'message_id': message_id}
            )

            update.message.reply_text(
                f"Сообщение запланировано на {schedule_time.strftime('%Y-%m-%d %H:%M')}\n"
                f"ID сообщения: {message_id}"
            )
        except ValueError:
            update.message.reply_text(
                "Неверный формат времени. Пожалуйста, используйте формат 'ГГГГ-ММ-ДД ЧЧ:ММ'"
            )
            return WAITING_FOR_SCHEDULE_TIME

        return ConversationHandler.END

    def send_scheduled_message(self, context: CallbackContext):
        job = context.job
        message_id = job.context['message_id']
        
        # Находим сообщение в списке
        for message in self.scheduled_messages:
            if message['id'] == message_id and not message['sent']:
                # Отправляем сообщение игроку
                if self.player_id:
                    context.bot.send_message(
                        self.player_id,
                        message['text']
                    )
                    # Отмечаем сообщение как отправленное
                    message['sent'] = True
                    BOT_CONFIG['scheduled_messages'] = self.scheduled_messages
                    
                    # Уведомляем админа
                    context.bot.send_message(
                        self.admin_id,
                        f"Запланированное сообщение (ID: {message_id}) было отправлено игроку"
                    )
                break

    def list_scheduled_messages(self, update: Update, context: CallbackContext):
        if update.effective_user.id != self.admin_id:
            return

        if not self.scheduled_messages:
            update.message.reply_text("Нет запланированных сообщений")
            return

        message_text = "Запланированные сообщения:\n\n"
        for msg in self.scheduled_messages:
            if not msg['sent']:
                schedule_time = datetime.fromisoformat(msg['time'])
                message_text += f"ID: {msg['id']}\n"
                message_text += f"Время: {schedule_time.strftime('%Y-%m-%d %H:%M')}\n"
                message_text += f"Текст: {msg['text']}\n\n"

        update.message.reply_text(message_text)

    def cancel_scheduled_message(self, update: Update, context: CallbackContext):
        if update.effective_user.id != self.admin_id:
            return

        try:
            message_id = int(context.args[0])
            for msg in self.scheduled_messages:
                if msg['id'] == message_id and not msg['sent']:
                    msg['sent'] = True
                    BOT_CONFIG['scheduled_messages'] = self.scheduled_messages
                    update.message.reply_text(f"Сообщение с ID {message_id} отменено")
                    return
            update.message.reply_text("Сообщение не найдено или уже отправлено")
        except (IndexError, ValueError):
            update.message.reply_text("Пожалуйста, укажите ID сообщения: /cancel_scheduled <id>")

    def handle_player_message(self, update: Update, context: CallbackContext) -> None:
        user_id = update.effective_user.id
        
        if user_id == self.player_id:
            # Пересылаем сообщение админу
            if update.message.photo:
                # Если прислано фото
                photo = update.message.photo[-1]
                context.bot.send_photo(
                    self.admin_id,
                    photo.file_id,
                    caption="Игрок прислал фото:"
                )
            else:
                # Если прислан текст
                context.bot.send_message(
                    self.admin_id,
                    f"Сообщение от игрока:\n{update.message.text}"
                )
        elif user_id == self.admin_id:
            # Обработка сообщений от админа
            if not context.user_data.get('waiting_for_task'):
                update.message.reply_text(
                    "Используйте команды /send_task или /schedule_message для взаимодействия с игроком"
                )

def main() -> None:
    print("Script started")
    
    # Убеждаемся, что запущен только один экземпляр
    single_instance = SingleInstance()
    
    print("Starting bot...")
    try:
        updater = Updater("8135956322:AAEwpxa3g9XujJO6z7RQ-pJqMp-EL7PwjbE", use_context=True)
        print("Updater created successfully")
        
        dp = updater.dispatcher
        print("Dispatcher initialized")
        
        # Создаем один экземпляр бота
        quest_bot = QuestBot()
        
        # Добавляем обработчик ошибок
        def error_callback(update, context):
            logger.error(f'Update "{update}" caused error "{context.error}"')

        dp.add_error_handler(error_callback)

        # Добавляем обработчики команд
        dp.add_handler(CommandHandler("start", quest_bot.start))
        dp.add_handler(CommandHandler("help", quest_bot.help_command))
        dp.add_handler(CommandHandler("list_scheduled", quest_bot.list_scheduled_messages))
        dp.add_handler(CommandHandler("cancel_scheduled", quest_bot.cancel_scheduled_message))

        task_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('send_task', quest_bot.send_task)],
            states={
                WAITING_FOR_TASK: [MessageHandler(Filters.text & ~Filters.command, quest_bot.process_task)],
            },
            fallbacks=[],
        )
        dp.add_handler(task_conv_handler)

        schedule_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('schedule_message', quest_bot.schedule_message)],
            states={
                WAITING_FOR_SCHEDULE_MESSAGE: [MessageHandler(Filters.text & ~Filters.command, quest_bot.save_scheduled_message)],
                WAITING_FOR_SCHEDULE_TIME: [MessageHandler(Filters.text & ~Filters.command, quest_bot.process_schedule_time)],
            },
            fallbacks=[],
        )
        dp.add_handler(schedule_conv_handler)

        dp.add_handler(MessageHandler(Filters.all & ~Filters.command, quest_bot.handle_player_message))

        print("Starting polling...")
        updater.start_polling(clean=True)
        print("Bot is running!")
        updater.idle()
    except Exception as e:
        print(f"Error starting bot: {e}")

if __name__ == '__main__':
    main()
