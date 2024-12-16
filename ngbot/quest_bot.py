import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import json
import os
from datetime import datetime
import pytz

# Константы для состояний
WAITING_FOR_TASK = 1
WAITING_FOR_SCHEDULE_MESSAGE = 2
WAITING_FOR_SCHEDULE_TIME = 3

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class QuestBot:
    def __init__(self):
        self.config = self.load_config()
        self.admin_id = self.config.get('admin_id')
        self.player_id = self.config.get('player_id')
        self.scheduled_messages = self.config.get('scheduled_messages', [])
        
    def load_config(self):
        config_path = 'config.json'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {'admin_id': None, 'player_id': None, 'scheduled_messages': []}
    
    def save_config(self):
        with open('config.json', 'w') as f:
            json.dump({
                'admin_id': self.admin_id,
                'player_id': self.player_id,
                'scheduled_messages': self.scheduled_messages
            }, f)

    def start(self, update: Update, context: CallbackContext) -> None:
        user_id = update.effective_user.id
        
        if not self.admin_id:
            self.admin_id = user_id
            self.save_config()
            update.message.reply_text("Вы зарегистрированы как администратор! Используйте /help для просмотра команд.")
            return

        if not self.player_id and user_id != self.admin_id:
            self.player_id = user_id
            self.save_config()
            update.message.reply_text("Добро пожаловать в квест! Ждите задание от хозяина игры.")
            context.bot.send_message(
                self.admin_id,
                f"Игрок присоединился к квесту! Используйте /send_task для отправки задания."
            )
            return

        if user_id == self.admin_id:
            update.message.reply_text("Вы администратор квеста. Используйте /help для просмотра команд.")
        elif user_id == self.player_id:
            update.message.reply_text("Добро пожаловать обратно в квест!")
        else:
            update.message.reply_text("Извините, этот бот предназначен только для одного игрока.")

    def help_command(self, update: Update, context: CallbackContext) -> None:
        if update.effective_user.id == self.admin_id:
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
            self.save_config()

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
                    self.save_config()
                    
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
                    self.save_config()
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
    # Создаем экземпляр бота
    bot = QuestBot()
    
    try:
        # Инициализируем updater с clean=True для очистки предыдущих сессий
        updater = Updater("8135956322:AAEwpxa3g9XujJO6z7RQ-pJqMp-EL7PwjbE", use_context=True)

        # Получаем диспетчер
        dp = updater.dispatcher

        # Добавляем обработчик ошибок
        def error_callback(update, context):
            logger.error(f'Update "{update}" caused error "{context.error}"')

        dp.add_error_handler(error_callback)

        # Добавляем обработчики команд
        dp.add_handler(CommandHandler("start", bot.start))
        dp.add_handler(CommandHandler("help", bot.help_command))
        dp.add_handler(CommandHandler("list_scheduled", bot.list_scheduled_messages))
        dp.add_handler(CommandHandler("cancel_scheduled", bot.cancel_scheduled_message))

        # Создаем обработчик диалога для отправки задания
        task_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('send_task', bot.send_task)],
            states={
                WAITING_FOR_TASK: [MessageHandler(Filters.text & ~Filters.command, bot.process_task)],
            },
            fallbacks=[],
        )
        dp.add_handler(task_conv_handler)

        # Создаем обработчик диалога для планирования сообщений
        schedule_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('schedule_message', bot.schedule_message)],
            states={
                WAITING_FOR_SCHEDULE_MESSAGE: [MessageHandler(Filters.text & ~Filters.command, bot.save_scheduled_message)],
                WAITING_FOR_SCHEDULE_TIME: [MessageHandler(Filters.text & ~Filters.command, bot.process_schedule_time)],
            },
            fallbacks=[],
        )
        dp.add_handler(schedule_conv_handler)

        # Обработчик всех остальных сообщений
        dp.add_handler(MessageHandler(Filters.all & ~Filters.command, bot.handle_player_message))

        # Запускаем бота
        updater.start_polling()
        updater.idle()
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")

if __name__ == '__main__':
    main()
