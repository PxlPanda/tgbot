FROM python:3.12-slim

# Создаем обе директории на всякий случай
RUN mkdir -p /app /APP

# Копируем во все возможные места
COPY quest_bot.py /app/
COPY quest_bot.py /APP/
COPY config.json /app/
COPY config.json /APP/
COPY requirements.txt /app/
COPY requirements.txt /APP/

# Показываем что где есть
RUN echo "=== /app ===" && ls -la /app && echo "=== /APP ===" && ls -la /APP

# Устанавливаем зависимости
RUN pip install -r /app/requirements.txt

# Пробуем запустить, используя оба пути
CMD sh -c "python /APP/quest_bot.py || python /app/quest_bot.py"
