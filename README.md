# Gemini Review MCP 서버

Gemini AI를 활용한 코드 리뷰 및 개선 제안 MCP 서버입니다.

## 🎯 주요 기능

### 자동화된 코드 분석
1. **Gemini로 우선순위 기반 리뷰** - 보안, 성능, 코드 품질을 4단계 우선순위로 분석
2. **지능적 개선 판단** - CRITICAL/HIGH 우선순위 이슈 발견 시 자동 개선 제안 생성
3. **구조화된 결과 제공** - 우선순위별 이슈 분류와 상세 개선 제안

### 🎯 우선순위 기반 리뷰 시스템
- 🔴 **CRITICAL**: 보안 취약점, 데이터 손실 위험, 시스템 크래시
- 🟡 **HIGH**: 성능 문제, 유지보수성 문제, 로직 오류
- 🟠 **MEDIUM**: 코드 스타일 문제, 경미한 비효율성, 검증 누락
- 🟢 **LOW**: 문서화, 네이밍 개선, 경미한 최적화

## 🛠️ MCP 도구

### `gemini_review`
코드 개선 분석 및 제안 생성
```json
{
  "code": "def hello(): print('hello')",
  "request": "보안과 성능 개선",
  "language": "python",
  "requirements": ["security", "performance", "best-practices", "readability"]
}
```

**파라미터:**
- `code` (필수): 분석할 코드
- `request` (선택): 추가 요청사항
- `language` (선택): 프로그래밍 언어 (기본값: auto-detect)
- `requirements` (선택): 집중 분석 영역 배열 (기본값: security, performance, best-practices, readability)

## 🚀 설치 및 설정

### 1. 환경 설정
```bash
# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 패키지 설치
pip install -r requirements.txt
```

### 2. API 키 설정
```bash
# .env 파일 생성
cp .env.example .env
```

`.env` 파일 편집:
```bash
# API Keys
GEMINI_API_KEY=your_gemini_api_key_here

# Model Configuration
GEMINI_MODEL=gemini-2.5-pro-preview-06-05
GEMINI_MODEL_FALLBACK=gemini-2.5-flash-preview-05-20
```

### 3. MCP 서버 실행 테스트
```bash
# 서버가 정상 실행되는지 확인
source .venv/bin/activate
python src/main.py
```

### 4. Claude Code에서 MCP 서버 연결
```bash
# MCP 서버 추가 (stdio 방식)
claude mcp add gemini-review stdio python src/main.py

# 또는 설정 파일에서 직접 추가
# ~/.config/claude-code/mcp.json
{
  "servers": {
    "gemini-review": {
      "command": "python",
      "args": ["src/main.py"],
      "cwd": "/path/to/gemini-review"
    }
  }
}
```

## 📋 사용법

Claude Code에서 자동으로 `gemini_review` 도구를 호출합니다:

```
"이 코드 개선해줘
```python
def login(username, password):
    if username == "admin" and password == "1234":
        return True
    return False
```"
```

**결과:**
- 🔍 Gemini가 코드 품질, 보안, 성능 등을 분석
- 📋 우선순위별 구조화된 리뷰 결과:
  - 🔴 **CRITICAL**: 보안 취약점, 시스템 크래시 위험
  - 🟡 **HIGH**: 성능 문제, 로직 오류
  - 🟠 **MEDIUM**: 코드 스타일, 경미한 비효율성
  - 🟢 **LOW**: 문서화, 네이밍 개선
- 💡 CRITICAL/HIGH 이슈가 있으면 자동으로 개선 제안 생성

## 🎛️ 환경변수 설정

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `GEMINI_API_KEY` | Gemini API 키 | 필수 |
| `GEMINI_MODEL` | 메인 Gemini 모델 | `gemini-2.0-flash-001` |
| `GEMINI_MODEL_FALLBACK` | Fallback Gemini 모델 | `gemini-2.0-flash-001` |
| `MCP_SERVER_NAME` | MCP 서버 이름 | `gemini-review` |
| `MCP_SERVER_VERSION` | MCP 서버 버전 | `0.1.0` |
| `MAX_TOKENS` | 최대 토큰 수 | `4096` |
| `TEMPERATURE` | 생성 온도 | `0.7` |

## 🏗️ 아키텍처

```
사용자 요청 → Claude Code → MCP Server
                              ↓
                    WorkflowManager
                    (워크플로우 조정)
                              ↓
                        GeminiClient
                              ↓
                         Gemini API
```

### 핵심 컴포넌트
- **`main.py`**: MCP 서버 진입점, 도구 등록 및 요청 처리
- **`workflow.py`**: 워크플로우 관리, 리뷰/개선 제안 조율
- **`gemini_client.py`**: Gemini API 클라이언트, 코드 리뷰 및 개선 제안 담당
- **`config/settings.py`**: 환경변수 기반 설정 관리

## 🤔 문제 해결

### 자주 발생하는 문제

**1. API 키 오류**
```
AuthenticationError: Invalid API key
```
→ `.env` 파일의 API 키를 확인하세요

**2. 모델 접근 오류**
```
Model not found or not accessible
```
→ `.env` 파일의 모델명이 올바른지 확인하세요

**3. 패키지 import 오류**
```
ModuleNotFoundError: No module named 'google.generativeai'
```
→ `pip install -r requirements.txt`로 의존성을 재설치하세요

**4. MCP 연결 실패**
→ MCP 서버가 실행 중인지 확인하고 Claude Code를 재시작하세요

## 📈 확장 가능성

### 추가 가능한 기능
- **우선순위별 자동 처리**: CRITICAL은 즉시 차단, HIGH는 경고, MEDIUM/LOW는 제안
- **커스텀 우선순위 규칙**: 프로젝트별 맞춤 우선순위 기준 설정
- 다른 AI 모델 지원 (GPT 등)
- 코드 테스트 자동 생성
- 보안 스캔 통합 (CRITICAL 우선순위 자동 감지)
- 성능 벤치마크 자동 실행 (HIGH 우선순위 성능 이슈 검증)
- 다양한 프로그래밍 언어 지원 확장

### 커스터마이징
- `workflow.py`의 워크플로우 로직 수정
- `settings.py`에서 추가 설정 옵션 구현
- 새로운 MCP 도구 추가

## 📄 라이선스

MIT License

---

🚀 **Gemini AI로 더 나은 코드를 만들어보세요!**