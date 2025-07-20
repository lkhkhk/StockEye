FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY pytest.ini ./
COPY src/bot/ ./src/bot/
COPY src/common/ ./src/common/
ENV PYTHONPATH=/app:/app/src
CMD ["python", "src/bot/main.py"] 