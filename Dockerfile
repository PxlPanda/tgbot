FROM python:3.12-slim

# Копируем в корень
COPY quest_bot.py .
COPY config.json .
COPY requirements.txt .

# Показываем где мы и что тут есть
RUN pwd && ls -la

# Устанавливаем зависимости
RUN pip install -r requirements.txt

# Запускаем из текущей директории
CMD ["python", "./quest_bot.py"]
