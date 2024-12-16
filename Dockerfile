FROM python:3.12-slim

WORKDIR /tgbot

# Копируем файлы зависимостей
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код и конфигурацию
COPY quest_bot.py ./
COPY config.json ./

# Запускаем бота
CMD ["python", "quest_bot.py"]
