FROM python:3.8.1-slim-buster

RUN mkdir -p /blanc

WORKDIR /blanc

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt /blanc/requirements.txt
RUN pip install -r requirements.txt --use-deprecated=legacy-resolver

# copy project
COPY . /blanc/

EXPOSE 5000

CMD chmod +x ./entrypoint.sh

ENTRYPOINT ["sh", "entrypoint.sh"]
