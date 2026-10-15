FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system utilities (git for repository scanners and tests, libpq5 for postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY tester/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY tester/backend .

EXPOSE 8000

# Bind dynamically to the port provided by Render / cloud provider
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
