FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for Pillow, psycopg2, and network wait utils
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Create directories for staticfiles and media
RUN mkdir -p /app/staticfiles /app/media

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120"]
