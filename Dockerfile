FROM python:3.12-slim

# Создаем эту чертову директорию
RUN mkdir -p /app

# Копируем все в нее
COPY quest_bot.py /app/
COPY config.json /app/
COPY requirements.txt /app/

# Переходим в нее
WORKDIR /app

# Показываем что там есть
RUN pwd && ls -la /app

# Устанавливаем зависимости
RUN pip install -r /app/requirements.txt

# Запускаем с полным путем
ENTRYPOINT ["python", "/app/quest_bot.py"]
