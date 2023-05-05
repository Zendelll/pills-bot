FROM python:3

WORKDIR /usr/src/app

RUN mkdir ./logs
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .