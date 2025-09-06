# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Prevent Python from writing .pyc files and enable stdout logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TOKENIZERS_PARALLELISM=false

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . .

# Default environment variables
ENV APP_MODULE=app.main:app
ENV HOST=0.0.0.0
ENV PORT=8000
ENV WORKERS=4
ENV RELOAD=false

# Expose app port
EXPOSE 8000

# Command
CMD if [ "$RELOAD" = "true" ]; then \
      exec uvicorn --reload $APP_MODULE --host $HOST --port $PORT; \
    else \
      exec uvicorn $APP_MODULE --host $HOST --port $PORT --workers $WORKERS; \
    fi
