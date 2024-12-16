FROM python:3.12-slim

RUN mkdir -p /app
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY quest_bot.py .
COPY config.json .
