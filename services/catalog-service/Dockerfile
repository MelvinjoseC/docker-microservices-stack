# Build stage
FROM golang:1.21-alpine AS build

WORKDIR /app
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o main .

# Production stage
FROM alpine:3.19

RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=build /app/main .

# Security Hardening: Create non-root group and user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

EXPOSE 8080

CMD ["./main"]
