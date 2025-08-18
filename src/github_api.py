"""GitHub API 클라이언트."""

import logging
from typing import Dict, Any, Optional
import requests
import time

from config import settings

logger = logging.getLogger(__name__)


class GitHubAPIClient:
    """GitHub API와의 상호작용을 담당하는 클라이언트."""
    
    def __init__(self):
        """GitHub API 클라이언트를 초기화합니다."""
        self.github_token = getattr(settings, 'github_token', None)
        self.default_repo = getattr(settings, 'default_github_repo', None)
        
        if not self.github_token:
            logger.warning("GitHub 토큰이 설정되지 않음 - 일부 기능이 제한됩니다")
    
    async def fetch_issue(self, repo: str, issue_number: int) -> Dict[str, Any]:
        """
        GitHub API에서 이슈 정보를 가져옵니다.
        
        Args:
            repo: "소유자/저장소" 형식의 저장소
            issue_number: 이슈 번호
            
        Returns:
            이슈 데이터 또는 오류
        """
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                if not self.github_token:
                    return {
                        "success": False,
                        "error": "GitHub 토큰이 설정되지 않았습니다. GITHUB_TOKEN 환경변수를 설정해주세요."
                    }
                
                # 저장소 형식 검증
                if not repo or '/' not in repo:
                    return {
                        "success": False,
                        "error": f"저장소 형식이 올바르지 않습니다. '소유자/저장소' 형식으로 입력해주세요. 입력값: {repo}"
                    }
                
                # 이슈 번호 검증
                if not isinstance(issue_number, int) or issue_number <= 0:
                    return {
                        "success": False,
                        "error": f"유효하지 않은 이슈 번호입니다. 양의 정수를 입력해주세요. 입력값: {issue_number}"
                    }
                
                url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
                headers = {
                    "Authorization": f"token {self.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "gemini-review-mcp/1.0"
                }
                
                logger.info(f"GitHub API 호출 시도 {attempt + 1}/{max_retries}: {url}")
                
                response = requests.get(url, headers=headers, timeout=30)
                
                # 상태 코드별 상세 처리
                if response.status_code == 200:
                    issue_data = response.json()
                    
                    # 이슈가 Pull Request인지 확인
                    if "pull_request" in issue_data:
                        return {
                            "success": False,
                            "error": f"#{issue_number}은 이슈가 아닌 Pull Request입니다. 이슈 번호를 확인해주세요."
                        }
                    
                    # 필요한 정보 추출
                    issue_info = {
                        "number": issue_data["number"],
                        "title": issue_data["title"],
                        "body": issue_data.get("body", ""),
                        "labels": [label["name"] for label in issue_data.get("labels", [])],
                        "assignees": [assignee["login"] for assignee in issue_data.get("assignees", [])],
                        "state": issue_data["state"],
                        "created_at": issue_data["created_at"],
                        "html_url": issue_data["html_url"],
                        "user": issue_data["user"]["login"]
                    }
                    
                    # 이슈 상태 검증
                    if issue_info["state"] == "closed":
                        logger.warning(f"이슈 #{issue_number}는 이미 닫힌 상태입니다")
                    
                    return {
                        "success": True,
                        "issue": issue_info,
                        "message": f"이슈 정보를 성공적으로 가져왔습니다: {issue_info['title']}"
                    }
                
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "error": f"{repo} 저장소에서 이슈 #{issue_number}를 찾을 수 없습니다. 저장소명과 이슈 번호를 확인해주세요."
                    }
                elif response.status_code == 401:
                    return {
                        "success": False,
                        "error": "GitHub 토큰이 유효하지 않습니다. GITHUB_TOKEN을 확인하고 필요한 권한이 있는지 확인해주세요."
                    }
                elif response.status_code == 403:
                    if "rate limit" in response.text.lower():
                        return {
                            "success": False,
                            "error": "GitHub API 레이트 리밋에 도달했습니다. 잠시 후 다시 시도해주세요."
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"{repo} 저장소에 접근 권한이 없습니다. 저장소가 비공개이거나 토큰 권한이 부족합니다."
                        }
                elif response.status_code >= 500:
                    # 서버 오류 시 재시도
                    if attempt < max_retries - 1:
                        logger.warning(f"GitHub API 서버 오류 (시도 {attempt + 1}/{max_retries}): {response.status_code}")
                        time.sleep(retry_delay * (attempt + 1))  # 지수 백오프
                        continue
                    else:
                        return {
                            "success": False,
                            "error": f"GitHub API 서버 오류가 지속됩니다: {response.status_code}"
                        }
                else:
                    return {
                        "success": False,
                        "error": f"예상치 못한 GitHub API 응답: {response.status_code} - {response.text[:200]}"
                    }
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(f"GitHub API 시간 초과 (시도 {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                return {
                    "success": False,
                    "error": "GitHub API 요청 시간이 초과되었습니다. 네트워크 연결을 확인해주세요."
                }
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    logger.warning(f"GitHub API 연결 오류 (시도 {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                return {
                    "success": False,
                    "error": "GitHub API에 연결할 수 없습니다. 인터넷 연결을 확인해주세요."
                }
            except requests.exceptions.RequestException as e:
                return {
                    "success": False,
                    "error": f"GitHub API 요청 오류: {str(e)}"
                }
            except ValueError as e:
                return {
                    "success": False,
                    "error": f"GitHub API 응답 파싱 오류: {str(e)}"
                }
            except Exception as e:
                logger.error(f"예상치 못한 오류: {str(e)}")
                return {
                    "success": False,
                    "error": f"예상치 못한 오류가 발생했습니다: {str(e)}"
                }
        
        # 모든 재시도 실패
        return {
            "success": False,
            "error": f"GitHub API 호출이 {max_retries}번 모두 실패했습니다"
        }


# 전역 인스턴스
github_api_client = None


async def get_github_api_client() -> GitHubAPIClient:
    """GitHub API 클라이언트 인스턴스를 가져오거나 생성합니다."""
    global github_api_client
    if github_api_client is None:
        github_api_client = GitHubAPIClient()
    return github_api_client