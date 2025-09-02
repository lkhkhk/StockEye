# Base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set python path
ENV PYTHONPATH=/app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/worker/ /app/src/worker
COPY src/common/ /app/src/common

# Command to run the service
CMD ["python", "src/worker/main.py"]