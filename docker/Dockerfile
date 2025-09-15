FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
  && apt-get -y install --no-install-recommends \
  postgresql-client \
  python3-pip \
  netcat-traditional \
  gettext

COPY ./requirements.txt /requirements.txt

RUN --mount=type=cache,target=/root/.cache pip install --upgrade pip
RUN --mount=type=cache,target=/root/.cache pip install -r requirements.txt

RUN useradd -ms /bin/bash app

ENV HOME=/home/app
ENV APP_HOME=/home/app/web

RUN mkdir -p $APP_HOME $APP_HOME/static

WORKDIR $APP_HOME

# copy project
COPY --chown=app:app . $APP_HOME

RUN chown -R app:app $APP_HOME/static

# change to the app user
USER app

RUN python manage.py collectstatic

ENTRYPOINT ["/home/app/web/docker/entrypoint.sh"]

CMD ["gunicorn", "-w", "2", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
