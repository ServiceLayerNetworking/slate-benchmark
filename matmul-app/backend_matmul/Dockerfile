FROM python:3.10

WORKDIR /app

RUN apt-get update
RUN apt-get install htop -y
RUN apt-get install python3-pip -y

COPY requirements.txt /app
RUN --mount=type=cache,target=/root/.cache/pip pip3 install -r requirements.txt

COPY . /app

ENTRYPOINT ["python3"]
CMD ["matmul.py"]
