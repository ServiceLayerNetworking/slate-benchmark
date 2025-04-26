FROM golang:1.21-alpine

WORKDIR /app
COPY main.go .

RUN go mod init app && go mod tidy && go build -o app .

ENV GOMAXPROCS=1

CMD ["./app"]
