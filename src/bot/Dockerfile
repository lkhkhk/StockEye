FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
# Force reinstall httpx to fix potential corruption

COPY pytest.ini /app/
COPY src/bot/ /app/src/bot/
COPY src/common/ /app/src/common/
ENV PYTHONPATH=/app:/app/src
# Dummy comment to force rebuild - Attempt 12
CMD ["python", "src/bot/main.py"]