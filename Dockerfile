FROM python:3.12-slim

# Создаем рабочую директорию
WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Копируем файлы бота
COPY quest_bot.py /app/
COPY config.json /app/

# Открываем порт
EXPOSE 80

# Проверяем содержимое и запускаем
RUN ls -la /app && pwd
CMD ["python", "/app/quest_bot.py"]
