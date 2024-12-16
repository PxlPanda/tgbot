FROM python:3.12-slim

# Сначала копируем файлы в корень
COPY quest_bot.py quest_bot.py
COPY config.json config.json
COPY requirements.txt requirements.txt

# Устанавливаем зависимости
RUN pip install -r requirements.txt

# Создаем и переходим в /app ПОСЛЕ копирования файлов
RUN mkdir -p /app
RUN cp quest_bot.py /app/ && \
    cp config.json /app/ && \
    cp requirements.txt /app/

# Показываем содержимое обоих мест
RUN echo "=== Root ===" && ls -la && echo "=== /app ===" && ls -la /app

WORKDIR /app
CMD ["python", "quest_bot.py"]
