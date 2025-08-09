# Base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set python path
ENV PYTHONPATH=/app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/worker/ /app/src/worker
COPY src/common/ /app/src/common
COPY src/api/models/ /app/src/api/models
COPY src/api/services/ /app/src/api/services
COPY src/api/schemas/ /app/src/api/schemas

# Set working directory for the service
WORKDIR /app/src/worker

# Command to run the service
CMD ["python", "main.py"]
