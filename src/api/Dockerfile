FROM python:3.10-slim

WORKDIR /app
ENV PYTHONPATH=/app

# 프로젝트 루트에 있는 requirements.txt를 복사
COPY requirements.txt ./

# 의존성 설치
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 필요한 소스코드만 컨테이너에 복사
COPY src/api/ /app/src/api
COPY src/common/ /app/src/common
COPY src/bot/ /app/src/bot

# uvicorn 서버 실행 (작업 디렉토리를 /app/src/api로 변경)
WORKDIR /app/src/api
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 