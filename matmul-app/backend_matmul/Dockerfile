FROM python:3.10-slim

WORKDIR /app

RUN apt-get update
RUN apt-get install htop -y

COPY requirements.txt /app
RUN --mount=type=cache,target=/root/.cache/pip pip3 install -r requirements.txt

COPY . /app
COPY ./vimrc_file /root/.vimrc

ENTRYPOINT ["python3"]
CMD ["matmul.py"]