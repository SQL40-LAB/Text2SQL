# 파이썬 3.10 슬림 버전 사용 (용량 최적화)
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 패키지 설치를 위해 requirements.txt 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스코드 전체 복사
COPY . .

# Streamlit 기본 포트 노출
EXPOSE 8501

# 컨테이너 실행 시 Streamlit 구동 명령어
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]