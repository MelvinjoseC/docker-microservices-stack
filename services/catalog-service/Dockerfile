FROM golang:1.21-alpine

WORKDIR /app

COPY go.mod ./
# Download dependencies
RUN go mod download

COPY . .

RUN go build -o main .

EXPOSE 8080

CMD ["./main"]
