FROM python:3.10-slim
WORKDIR /app
ENV PYTHONPATH=/app:/app/src
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY src/api/ ./src/api/
COPY src/common/ ./src/common/
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"] 