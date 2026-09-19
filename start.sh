#!/usr/bin/env bash
# 처음 한 번만: chmod +x start.sh
set -e
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  echo "가상환경 만드는 중..."
  python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "(.env 파일 생성함 — GEMINI_API_KEY는 나중에 채워도 됨, 없어도 일단 돌아감)"
fi

echo "서버 실행 중... http://localhost:8000 열기"
uvicorn main:app --reload --port 8000
