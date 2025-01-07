FROM python:3.9.2-slim

ENV TZ=Asia/Jerusalem

WORKDIR /app

RUN pip install --upgrade pip

RUN apt-get update && apt-get install build-essential -y

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python3", "bot.py"]
