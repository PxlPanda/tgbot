FROM python:3.12-slim

COPY . .
RUN pip install -r requirements.txt

RUN ls -la
CMD ["python", "quest_bot.py"]
