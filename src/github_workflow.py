"""GitHub 이슈 해결 워크플로우 매니저."""

import logging
import json
import os
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests
import subprocess

from gemini_client import get_gemini_client
from workflow import get_workflow_manager
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
        try:
            if not self.github_token:
                return {
                    "success": False,
                    "error": "GitHub 토큰이 설정되지 않았습니다"
                }
            
            url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "gemini-review-mcp/1.0"
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 404:
                return {
                    "success": False,
                    "error": f"{repo}에서 이슈 #{issue_number}를 찾을 수 없습니다"
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "error": "GitHub 토큰이 유효하지 않거나 만료되었습니다"
                }
            elif not response.ok:
                return {
                    "success": False,
                    "error": f"GitHub API 오류: {response.status_code} - {response.text}"
                }
            
            issue_data = response.json()
            
            # 필요한 정보 추출
            issue_info = {
                "number": issue_data["number"],
                "title": issue_data["title"],
                "body": issue_data.get("body", ""),
                "labels": [label["name"] for label in issue_data.get("labels", [])],
                "assignees": [assignee["login"] for assignee in issue_data.get("assignees", [])],
                "state": issue_data["state"],
                "created_at": issue_data["created_at"],
                "html_url": issue_data["html_url"]
            }
            
            return {
                "success": True,
                "issue": issue_info,
                "raw_data": issue_data
            }
            
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"이슈 가져오기 네트워크 오류: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"이슈 가져오기 오류: {str(e)}"
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