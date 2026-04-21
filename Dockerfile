# syntax=docker/dockerfile:1
FROM python:3.13-slim-bookworm

WORKDIR /python-docker

SHELL ["/bin/bash", "-c"]

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
RUN python3 -m venv venv
RUN source venv/bin/activate

EXPOSE 5000

COPY . .

#CMD ["python3", "app.py"]
CMD ["flask", "run", "--host=0.0.0.0"]
