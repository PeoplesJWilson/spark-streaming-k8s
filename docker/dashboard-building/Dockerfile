FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt /
COPY dash-app.py /

USER 0
RUN mkdir /assets
COPY assets /assets
USER $CONTAINER_USER_ID

RUN pip install --no-cache-dir -r /requirements.txt

COPY dash-app.py /

CMD [ "python", "/dash-app.py" ]