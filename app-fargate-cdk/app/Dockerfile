FROM --platform=linux/amd64 python:3.9-slim

WORKDIR /app

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY *.py .

# 필요한 디렉토리 생성
RUN mkdir -p ./chat_chunks ./analysis_results

# 실행 권한 추가
RUN chmod +x /app/*.py

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# 포트 노출
EXPOSE 8501

# 애플리케이션 실행
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
