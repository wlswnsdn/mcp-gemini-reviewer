"""GitHub 이슈 해결 워크플로우 매니저."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import requests
import time
import subprocess
import re

from config import settings

logger = logging.getLogger(__name__)


class GitHubIssueWorkflow:
    """GitHub 이슈 자동 해결 워크플로우를 관리합니다."""
    
    def __init__(self):
        """GitHub 워크플로우 매니저를 초기화합니다."""
        self.github_token = getattr(settings, 'github_token', None)
        self.default_repo = getattr(settings, 'default_github_repo', None)
        self.max_review_iterations = 3
        
        if not self.github_token:
            logger.warning("GitHub 토큰이 설정되지 않음 - 일부 기능이 제한됩니다")
    
    async def solve_issue(
        self,
        issue_number: int,
        repository: Optional[str] = None,
        base_branch: str = "develop"
    ) -> Dict[str, Any]:
        """
        GitHub 이슈를 자동화된 워크플로우로 해결합니다.
        
        Args:
            issue_number: GitHub 이슈 번호
            repository: "소유자/저장소" 형식의 저장소 (선택사항)
            base_branch: PR 기준 브랜치 (기본값: develop)
            
        Returns:
            모든 단계를 포함한 워크플로우 결과
        """
        workflow_id = self._generate_workflow_id()
        repo = repository or self.default_repo
        
        if not repo:
            return {
                "success": False,
                "error": "저장소가 지정되지 않았고 기본 설정도 없습니다"
            }
        
        result = {
            "workflow_id": workflow_id,
            "issue_number": issue_number,
            "repository": repo,
            "base_branch": base_branch,
            "stages": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 1단계: 이슈 정보 가져오기
            logger.info(f"1단계: {repo}에서 이슈 #{issue_number} 정보를 가져오는 중")
            issue_data = await self._fetch_issue(repo, issue_number)
            if not issue_data["success"]:
                result["success"] = False
                result["error"] = issue_data["error"]
                return result
            
            result["stages"]["issue_fetch"] = issue_data
            issue_info = issue_data["issue"]
            logger.info(f"이슈 정보 가져오기 완료: {issue_info['title']}")
            
            # Stage 2: 브랜치 생성 및 체크아웃
            logger.info("2단계: 이슈 해결용 브랜치 생성 및 체크아웃")
            branch_result = await self._create_and_checkout_branch(issue_info, base_branch)
            if not branch_result["success"]:
                result["success"] = False
                result["error"] = branch_result["error"]
                return result
            
            result["stages"]["branch_setup"] = branch_result
            logger.info(f"브랜치 설정 완료: {branch_result['branch_name']}")
            
            return result
            
        except Exception as e:
            logger.error(f"GitHub 워크플로우 오류: {str(e)}")
            result["success"] = False
            result["error"] = str(e)
            return result
    
    async def _fetch_issue(self, repo: str, issue_number: int) -> Dict[str, Any]:
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
    
    async def _create_and_checkout_branch(self, issue_info: Dict[str, Any], base_branch: str = "develop") -> Dict[str, Any]:
        """
        이슈 해결용 브랜치를 생성하고 체크아웃합니다.
        
        Args:
            issue_info: 이슈 정보
            base_branch: 기준 브랜치 (기본값: develop)
            
        Returns:
            브랜치 생성 결과
        """
        try:
            # 브랜치명 생성
            branch_name_result = self._generate_branch_name(issue_info)
            if not branch_name_result["success"]:
                return branch_name_result
            
            branch_name = branch_name_result["branch_name"]
            
            # 현재 git 상태 확인
            git_status = self._run_git_command(["status", "--porcelain"])
            if not git_status["success"]:
                return {
                    "success": False,
                    "error": f"Git 상태 확인 실패: {git_status['error']}"
                }
            
            # 변경사항이 있는지 확인
            if git_status["output"].strip():
                return {
                    "success": False,
                    "error": "작업 디렉토리에 커밋되지 않은 변경사항이 있습니다. 변경사항을 커밋하거나 스태시한 후 다시 시도해주세요.",
                    "uncommitted_changes": git_status["output"]
                }
            
            # 기준 브랜치로 체크아웃
            checkout_base = self._run_git_command(["checkout", base_branch])
            if not checkout_base["success"]:
                return {
                    "success": False,
                    "error": f"기준 브랜치 '{base_branch}' 체크아웃 실패: {checkout_base['error']}"
                }
            
            # 기준 브랜치 최신화 (origin에서 pull)
            logger.info(f"기준 브랜치 '{base_branch}' 최신화 중")
            pull_result = self._run_git_command(["pull", "origin", base_branch])
            if not pull_result["success"]:
                logger.warning(f"기준 브랜치 풀 실패 (계속 진행): {pull_result['error']}")
            
            # 브랜치 존재 여부 확인
            branch_exists = self._run_git_command(["show-ref", "--verify", f"refs/heads/{branch_name}"])
            if branch_exists["success"]:
                return {
                    "success": False,
                    "error": f"브랜치 '{branch_name}'가 이미 존재합니다. 다른 이름을 사용하거나 기존 브랜치를 삭제해주세요."
                }
            
            # 새 브랜치 생성 및 체크아웃
            create_branch = self._run_git_command(["checkout", "-b", branch_name])
            if not create_branch["success"]:
                return {
                    "success": False,
                    "error": f"브랜치 생성 실패: {create_branch['error']}"
                }
            
            # 브랜치 생성 확인
            current_branch = self._run_git_command(["branch", "--show-current"])
            if not current_branch["success"] or current_branch["output"].strip() != branch_name:
                return {
                    "success": False,
                    "error": f"브랜치 체크아웃 확인 실패. 현재 브랜치: {current_branch.get('output', '알 수 없음')}"
                }
            
            return {
                "success": True,
                "branch_name": branch_name,
                "base_branch": base_branch,
                "current_branch": current_branch["output"].strip(),
                "message": f"브랜치 '{branch_name}'를 성공적으로 생성하고 체크아웃했습니다",
                "pattern_used": branch_name_result.get("pattern_source", "기본값")
            }
            
        except Exception as e:
            logger.error(f"브랜치 생성 오류: {str(e)}")
            return {
                "success": False,
                "error": f"브랜치 생성 중 예상치 못한 오류: {str(e)}"
            }
    
    def _generate_branch_name(self, issue_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        이슈 정보를 바탕으로 브랜치명을 생성합니다.
        
        Args:
            issue_info: 이슈 정보
            
        Returns:
            브랜치명 생성 결과
        """
        try:
            issue_number = issue_info["number"]
            body = issue_info.get("body", "")
            
            # 이슈 본문 첫 문장에서 브랜치 패턴 추출
            if body:
                first_line = body.split('\n')[0].strip()
                
                # 브랜치 패턴 정규식: (타입)/#숫자-영문명
                pattern = r'^(feat|fix|refactor|chore|build)/#\d+-([a-zA-Z0-9-]+)$'
                match = re.match(pattern, first_line)
                
                if match:
                    branch_type = match.group(1)
                    branch_suffix = match.group(2)
                    branch_name = f"{branch_type}/#{issue_number}-{branch_suffix}"
                    
                    # 브랜치명 유효성 검증
                    if self._validate_branch_name(branch_name):
                        return {
                            "success": True,
                            "branch_name": branch_name,
                            "pattern_source": "이슈 본문",
                            "message": f"이슈 본문에서 브랜치 패턴 추출: {first_line}"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"이슈 본문의 브랜치 패턴이 유효하지 않습니다: {first_line}"
                        }
            
            # 기본값: feat 타입으로 생성
            default_name = f"feat/#{issue_number}-issue"
            
            return {
                "success": True,
                "branch_name": default_name,
                "pattern_source": "기본값",
                "message": f"이슈 본문에 브랜치 패턴이 없어 기본값 사용: {default_name}"
            }
            
        except Exception as e:
            logger.error(f"브랜치명 생성 오류: {str(e)}")
            return {
                "success": False,
                "error": f"브랜치명 생성 중 오류: {str(e)}"
            }
    
    def _validate_branch_name(self, branch_name: str) -> bool:
        """
        브랜치명이 Git 규칙에 맞는지 검증합니다.
        
        Args:
            branch_name: 검증할 브랜치명
            
        Returns:
            유효성 여부
        """
        # Git 브랜치명 규칙
        # - ASCII 문자, 숫자, 하이픈, 언더스코어, 슬래시만 허용
        # - 특수문자 제한
        # - 연속된 점(..) 금지
        # - 시작/끝이 슬래시나 점이면 안됨
        
        if not branch_name or len(branch_name) > 100:
            return False
        
        # 허용되지 않는 문자 확인
        if re.search(r'[^\w\-/]', branch_name):
            return False
        
        # 연속된 슬래시 확인
        if '//' in branch_name:
            return False
        
        # 시작/끝 문자 확인
        if branch_name.startswith('/') or branch_name.endswith('/'):
            return False
        
        return True
    
    def _run_git_command(self, args: list) -> Dict[str, Any]:
        """
        Git 명령어를 실행합니다.
        
        Args:
            args: Git 명령어 인수 리스트
            
        Returns:
            명령어 실행 결과
        """
        try:
            cmd = ["git"] + args
            logger.debug(f"Git 명령어 실행: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout,
                    "command": ' '.join(cmd)
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr or result.stdout or "알 수 없는 Git 오류",
                    "command": ' '.join(cmd),
                    "return_code": result.returncode
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Git 명령어 시간 초과: {' '.join(cmd)}"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Git이 설치되지 않았거나 PATH에 없습니다"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Git 명령어 실행 오류: {str(e)}"
            }
    
    def _generate_workflow_id(self) -> str:
        """고유한 워크플로우 ID를 생성합니다."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"github_workflow_{timestamp}"


# 전역 인스턴스
github_workflow_manager = None


async def get_github_workflow_manager() -> GitHubIssueWorkflow:
    """GitHub 워크플로우 매니저 인스턴스를 가져오거나 생성합니다."""
    global github_workflow_manager
    if github_workflow_manager is None:
        github_workflow_manager = GitHubIssueWorkflow()
    return github_workflow_manager