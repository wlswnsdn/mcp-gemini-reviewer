#!/bin/bash

# 현재 스크립트 위치에서 프로젝트 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 가상환경이 없으면 생성
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment"
    python -m venv .venv
fi

# 가상환경 활성화
source .venv/bin/activate

# requirements.txt가 변경되었거나 의존성이 설치되지 않았으면 설치
if [ ! -f ".venv/installed" ] || [ "requirements.txt" -nt ".venv/installed" ]; then
    echo "Installing dependencies"
    pip install -r requirements.txt
    touch .venv/installed
fi

# MCP 서버 실행
exec python src/main.py