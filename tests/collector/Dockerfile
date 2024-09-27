FROM python:3.7.4

RUN apt-get update
RUN apt-get install -y python3-setuptools

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /usr/src/app

COPY test.py test.py
CMD [ "python", "test.py" ]
