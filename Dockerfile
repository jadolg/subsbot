FROM python:3.6.0-alpine

RUN apk update && apk add --no-cache pkgconfig python3-dev openssl-dev libffi-dev musl-dev make gcc
ADD requirements.txt /home/

WORKDIR /home/

RUN pip install -r requirements.txt

ADD . /home/

CMD ["/usr/local/bin/python", "main.py"]
