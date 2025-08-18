"""GitHub 이슈 해결 워크플로우 매니저."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from config import settings
from github_api import get_github_api_client
from git_operations import get_git_operations
from code_generator import get_code_generator

logger = logging.getLogger(__name__)


class GitHubIssueWorkflow:
    """GitHub 이슈 자동 해결 워크플로우를 관리합니다."""
    
    def __init__(self):
        """GitHub 워크플로우 매니저를 초기화합니다."""
        self.max_review_iterations = 3
    
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
        repo = repository or getattr(settings, 'default_github_repo', None)
        
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
            # Stage 1: 이슈 정보 가져오기
            logger.info(f"1단계: {repo}에서 이슈 #{issue_number} 정보를 가져오는 중")
            github_client = await get_github_api_client()
            issue_data = await github_client.fetch_issue(repo, issue_number)
            
            if not issue_data["success"]:
                result["success"] = False
                result["error"] = issue_data["error"]
                return result
            
            result["stages"]["issue_fetch"] = issue_data
            issue_info = issue_data["issue"]
            logger.info(f"이슈 정보 가져오기 완료: {issue_info['title']}")
            
            # Stage 2: 브랜치 생성 및 체크아웃
            logger.info("2단계: 이슈 해결용 브랜치 생성 및 체크아웃")
            git_ops = await get_git_operations()
            branch_result = await git_ops.create_and_checkout_branch(issue_info, base_branch)
            
            if not branch_result["success"]:
                result["success"] = False
                result["error"] = branch_result["error"]
                return result
            
            result["stages"]["branch_setup"] = branch_result
            logger.info(f"브랜치 설정 완료: {branch_result['branch_name']}")
            
            # Stage 3: 이슈 분석 및 코드 생성
            logger.info("3단계: 이슈 내용을 분석하여 코드 생성")
            code_gen = await get_code_generator()
            code_result = await code_gen.generate_code_from_issue(issue_info)
            
            if not code_result["success"]:
                result["success"] = False
                result["error"] = code_result["error"]
                return result
            
            result["stages"]["code_generation"] = code_result
            logger.info(f"코드 생성 완료: {len(code_result['generated_files'])}개 파일")
            
            # 성공적으로 완료
            result["success"] = True
            result["message"] = f"이슈 #{issue_number} 해결 워크플로우가 완료되었습니다"
            
            return result
            
        except Exception as e:
            logger.error(f"GitHub 워크플로우 오류: {str(e)}")
            result["success"] = False
            result["error"] = str(e)
            return result
    
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