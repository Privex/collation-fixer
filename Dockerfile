FROM python:3.8-buster

RUN apt update -y && apt install -y libmariadbclient-dev && apt clean -qy

WORKDIR /opt/app

RUN pip3 install -U pipenv

COPY Pipfile Pipfile.lock /opt/app/

RUN pipenv install --ignore-pipfile

COPY . /opt/app/

ENTRYPOINT [ "pipenv", "run", "/opt/app/app.py" ]

