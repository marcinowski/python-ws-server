FROM python:3.7.4-alpine

RUN apk update && apk add --update --no-cache supervisor gcc python3-dev musl-dev bash coreutils

WORKDIR /code

COPY ./requirements.txt /code/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /code/

RUN mkdir -p /etc/supervisor.d/
COPY ./notifications.ini /etc/supervisor.d/

WORKDIR /code/scripts

CMD ["./start.sh"]
