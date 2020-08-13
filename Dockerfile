FROM python:3.7-slim

RUN useradd --create-home --shell /bin/bash copytrack
#RUN adduser -D copytrack

WORKDIR /home/copytrack

COPY requirements.txt requirements.txt
#RUN apk add --no-cache --virtual .build-deps gcc musl-dev
#RUN pip install cython
RUN python -m venv venv && \
    venv/bin/pip install --upgrade pip && \
    venv/bin/pip install -r requirements.txt && \
    venv/bin/pip install gunicorn
#RUN apk del .build-deps gcc musl-dev

COPY webproject webproject
COPY migrations migrations
COPY tests tests
COPY app.py config.py sentry_settings.py boot.sh ./
RUN chmod a+x boot.sh

ENV FLASK_APP app.py

RUN chown -R copytrack:copytrack ./
USER copytrack

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]