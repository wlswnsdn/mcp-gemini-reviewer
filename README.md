# Gemini Review MCP 서버

Claude MCP를 활용해 다른 프로젝트에서 코드 구현 요청 → Claude 코드 생성 → Gemini 리뷰 → 피드백 반영의 자동화된 워크플로우를 제공하는 MCP 서버입니다.

## 🎯 주요 기능

### 자동화된 워크플로우
1. **Claude로 코드 생성** - 사용자 요청을 바탕으로 고품질 코드 구현
2. **Gemini로 코드 리뷰** - 보안, 성능, 코드 품질 등을 자동 검토
3. **피드백 기반 개선** - 리뷰 결과를 바탕으로 코드를 자동 개선
4. **최종 결과 제공** - 리뷰를 통과한 최종 코드 반환

### 지능적 의도 판단
- **구현 요청**: "FastAPI로 인증 API 만들어줘" → 전체 워크플로우 실행
- **리뷰 요청**: "이 코드 리뷰해줘" → Gemini 리뷰만 실행  
- **일반 질문**: "JWT가 뭐야?" → MCP 도구 사용 안함

## 🛠️ MCP 도구들

### `request_code_implementation`
코드 구현 요청을 처리하는 메인 워크플로우
```json
{
  "request": "FastAPI로 JWT 인증 API 구현해줘",
  "language": "python",
  "requirements": ["보안", "토큰 만료 처리"]
}
```

### `review_code_with_gemini`  
Gemini AI를 사용한 코드 리뷰
```json
{
  "code": "def hello(): print('hello')",
  "language": "python",
  "focus_areas": ["security", "performance"]
}
```

### `improve_code_with_feedback`
리뷰 피드백을 바탕으로 코드 개선
```json
{
  "original_code": "원본 코드",
  "feedback": "보안 취약점을 수정하고 성능을 개선하세요",
  "language": "python"  
}
```

### `get_review_history`
워크플로우 실행 히스토리 조회
```json
{
  "limit": 10
}
```

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
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Model Configuration  
CLAUDE_MODEL=claude-opus-4-1-20250805
GEMINI_MODEL=gemini-2.5-pro-preview-06-05

# Fallback models
CLAUDE_MODEL_FALLBACK=claude-sonnet-4-20250131
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

### 코드 구현 요청
```
"FastAPI로 JWT 토큰 기반 사용자 인증 API를 만들어줘"
```

**결과:**
- ✅ Claude가 코드 생성
- 🔍 Gemini가 자동 리뷰
- ⚡ 피드백 기반 개선 (필요시)
- 📝 최종 코드 반환

### 코드 리뷰 요청
```
"이 코드 리뷰해줘
```python
def login(username, password):
    # 간단한 로그인 함수
    if username == "admin" and password == "1234":
        return True
    return False
```"
```

**결과:**
- 🔍 Gemini가 코드 품질, 보안 등을 분석
- 📋 상세한 리뷰 결과 제공

## 🎛️ 환경변수 설정

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `ANTHROPIC_API_KEY` | Claude API 키 | 필수 |
| `GEMINI_API_KEY` | Gemini API 키 | 필수 |
| `CLAUDE_MODEL` | 메인 Claude 모델 | `claude-3-5-sonnet-20241022` |
| `GEMINI_MODEL` | 메인 Gemini 모델 | `gemini-2.0-flash-001` |
| `AUTO_REVIEW` | 자동 리뷰 활성화 | `true` |
| `AUTO_IMPROVE` | 자동 개선 활성화 | `true` |
| `MAX_TOKENS` | 최대 토큰 수 | `4096` |
| `TEMPERATURE` | 생성 온도 | `0.7` |

## 🏗️ 아키텍처

```
사용자 요청 → Claude Code → MCP Server
                              ↓
                    WorkflowManager
                    (의도 판단 및 워크플로우 조정)
                              ↓
                    ┌─────────┼─────────┐
                    ↓         ↓         ↓
              ClaudeClient GeminiClient 기타 도구들
                    ↓         ↓         ↓
                Claude API  Gemini API  로컬 처리
```

### 핵심 컴포넌트
- **`main.py`**: MCP 서버 진입점, 도구 등록 및 요청 처리
- **`workflow.py`**: 워크플로우 관리, 의도 판단
- **`claude_client.py`**: Claude API 클라이언트, 코드 생성 담당
- **`gemini_client.py`**: Gemini API 클라이언트, 코드 리뷰 담당
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
- 다른 AI 모델 지원 (GPT, Claude Haiku 등)
- 코드 테스트 자동 생성
- 보안 스캔 통합
- 성능 벤치마크 자동 실행
- 다양한 프로그래밍 언어 지원 확장

### 커스터마이징
- `workflow.py`의 의도 판단 로직 수정
- `settings.py`에서 추가 설정 옵션 구현
- 새로운 MCP 도구 추가

## 📄 라이선스

MIT License

---

🚀 **Claude + Gemini의 강력한 조합으로 더 나은 코드를 만들어보세요!**