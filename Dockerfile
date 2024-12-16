FROM python:3.12-slim

WORKDIR /app

COPY . /app/

RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1

CMD ["python", "quest_bot.py"]
