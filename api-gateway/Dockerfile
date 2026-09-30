FROM nginx:1.25-alpine

# Install curl for healthcheck validation
RUN apk add --no-cache curl

# Copy custom configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
