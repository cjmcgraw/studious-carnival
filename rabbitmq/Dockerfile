FROM rabbitmq:3.9-management-alpine
RUN apk update && apk upgrade && apk add python3-dev py3-pip

WORKDIR /app
ENV PATH ${PATH}:/app
COPY requirements.txt .
RUN pip install --user --upgrade pip && pip install --user -r requirements.txt
COPY read-from-exchange.py .
COPY write-to-exchange.py .
