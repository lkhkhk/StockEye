FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
# Force reinstall httpx to fix potential corruption
RUN pip uninstall -y httpx && pip install httpx
COPY pytest.ini ./
COPY src/bot/ ./src/bot/
COPY src/common/ ./src/common/
ENV PYTHONPATH=/app:/app/src
# Dummy comment to force rebuild - Attempt 12
CMD ["python", "src/bot/main.py"] 