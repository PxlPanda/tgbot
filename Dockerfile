FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/
COPY quest_bot.py /app/
COPY config.json /app/

RUN pip install -r requirements.txt

CMD ["python", "/app/quest_bot.py"]
