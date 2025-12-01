FROM python:3.11-slim
LABEL maintainer="benjamink0612@gmail.com"

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libpq-dev \
    libjpeg-dev zlib1g-dev \
  && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements.dev.txt /tmp/requirements.dev.txt

ARG DEV=false
RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    /py/bin/pip install --no-cache-dir -r /tmp/requirements.txt && \
    if [ "$DEV" = "true" ]; \
        then /py/bin/pip install --no-cache-dir -r /tmp/requirements.dev.txt ; \
    fi && \
    rm -rf /tmp

COPY ./scripts /scripts
COPY ./app /app

WORKDIR /app
EXPOSE 8000

RUN adduser \
        --disabled-password \
        --no-create-home \
        django-user && \
    chmod -R +x /scripts && \
    chown -R django-user:django-user /app /py /scripts

ENV PATH="/scripts:/py/bin:$PATH"

USER django-user

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
