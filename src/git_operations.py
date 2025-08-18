"""Git 명령어 실행 및 브랜치 관리."""

import logging
from typing import Dict, Any
import subprocess
import re

logger = logging.getLogger(__name__)


class GitOperations:
    """Git 명령어 실행 및 브랜치 관리를 담당하는 클래스."""
    
    def __init__(self):
        """Git 명령어 클라이언트를 초기화합니다."""
        pass
    
    async def create_and_checkout_branch(self, issue_info: Dict[str, Any], base_branch: str = "develop") -> Dict[str, Any]:
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
                return {
                    "success": False,
                    "error": f"기준 브랜치 최신화 실패: {pull_result['error']}. 네트워크 연결과 GitHub 권한을 확인해주세요."
                }
            
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


# 전역 인스턴스
git_operations = None


async def get_git_operations() -> GitOperations:
    """Git 명령어 클라이언트 인스턴스를 가져오거나 생성합니다."""
    global git_operations
    if git_operations is None:
        git_operations = GitOperations()
    return git_operations