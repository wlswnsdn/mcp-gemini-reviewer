"""이슈 기반 코드 생성 및 분석."""

import logging
from typing import Dict, Any
import re
import os
import string

from claude_client import get_claude_client

logger = logging.getLogger(__name__)


class CodeGenerator:
    """이슈를 분석하여 해결 코드를 생성하는 클래스."""
    
    def __init__(self):
        """코드 생성기를 초기화합니다."""
        pass
    
    async def generate_code_from_issue(self, issue_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        이슈 내용을 분석하여 해결 코드를 생성합니다.
        
        Args:
            issue_info: 이슈 정보
            
        Returns:
            코드 생성 결과
        """
        try:
            # 이슈 내용 분석
            analysis_result = self._analyze_issue_content(issue_info)
            
            # Claude에게 코드 생성 요청
            claude_client = await get_claude_client()
            
            # 코드 생성 프롬프트 구성
            prompt = self._build_code_generation_prompt(issue_info, analysis_result)
            
            # Claude에게 코드 생성 요청
            logger.info("Claude에게 코드 생성 요청 중")
            response = await claude_client.generate_code(prompt)
            
            if not response or not response.get("success"):
                return {
                    "success": False,
                    "error": response.get("error", "Claude에서 코드 생성 응답을 받지 못했습니다")
                }
            
            # 생성된 코드에서 파일별로 분리
            generated_code = response["generated_code"]
            files_result = self._parse_generated_code(generated_code, analysis_result)
            
            if not files_result["success"]:
                return files_result
            
            # 파일들을 실제로 저장
            save_result = self._save_generated_files(files_result["files"])
            if not save_result["success"]:
                return save_result
            
            return {
                "success": True,
                "generated_files": files_result["files"],
                "saved_files": save_result["saved_files"],
                "analysis": analysis_result,
                "raw_response": generated_code,
                "message": f"{len(files_result['files'])}개 파일이 생성되었습니다"
            }
            
        except Exception as e:
            logger.error(f"코드 생성 오류: {str(e)}")
            return {
                "success": False,
                "error": f"코드 생성 중 오류: {str(e)}"
            }
    
    def _analyze_issue_content(self, issue_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        이슈 내용을 분석하여 구현 방향을 결정합니다.
        
        Args:
            issue_info: 이슈 정보
            
        Returns:
            분석 결과
        """
        title = issue_info["title"]
        body = issue_info.get("body", "")
        labels = issue_info.get("labels", [])
        
        # 기본 분석
        analysis = {
            "task_type": "feature",  # feature, bugfix, refactor 등
            "programming_language": "python",  # 기본값
            "estimated_files": 1,
            "complexity": "medium",  # low, medium, high
            "keywords": []
        }
        
        # 라벨 기반 분석
        for label in labels:
            label_lower = label.lower()
            if "bug" in label_lower or "fix" in label_lower:
                analysis["task_type"] = "bugfix"
            elif "enhancement" in label_lower or "feature" in label_lower:
                analysis["task_type"] = "feature"
            elif "refactor" in label_lower:
                analysis["task_type"] = "refactor"
            
            # 언어 추정
            if any(lang in label_lower for lang in ["python", "js", "javascript", "typescript", "java", "go"]):
                analysis["programming_language"] = label_lower
        
        # 제목과 본문에서 키워드 추출
        content = f"{title} {body}".lower()
        
        # 언어 키워드
        if "python" in content or ".py" in content:
            analysis["programming_language"] = "python"
        elif "javascript" in content or ".js" in content or "react" in content:
            analysis["programming_language"] = "javascript"
        elif "typescript" in content or ".ts" in content:
            analysis["programming_language"] = "typescript"
        
        # 복잡도 추정
        if any(keyword in content for keyword in ["simple", "quick", "minor", "small"]):
            analysis["complexity"] = "low"
        elif any(keyword in content for keyword in ["complex", "major", "refactor", "redesign"]):
            analysis["complexity"] = "high"
        
        # 키워드 추출
        keywords = []
        common_keywords = ["api", "database", "auth", "test", "ui", "component", "service", "util"]
        for keyword in common_keywords:
            if keyword in content:
                keywords.append(keyword)
        analysis["keywords"] = keywords
        
        return analysis
    
    def _build_code_generation_prompt(self, issue_info: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """
        코드 생성을 위한 프롬프트를 구성합니다.
        
        Args:
            issue_info: 이슈 정보
            analysis: 이슈 분석 결과
            
        Returns:
            생성된 프롬프트
        """
        title = issue_info["title"]
        body = issue_info.get("body", "")
        language = analysis["programming_language"]
        task_type = analysis["task_type"]
        
        prompt_parts = [
            "당신은 전문 개발자입니다. 주어진 GitHub 이슈를 해결하는 코드를 생성해주세요.",
            f"\n## 이슈 정보",
            f"**제목**: {title}",
            f"**내용**:\n{body}",
            f"\n## 구현 요구사항",
            f"- 프로그래밍 언어: {language}",
            f"- 작업 유형: {task_type}",
            f"- 복잡도: {analysis['complexity']}",
        ]
        
        if analysis["keywords"]:
            prompt_parts.append(f"- 관련 키워드: {', '.join(analysis['keywords'])}")
        
        prompt_parts.extend([
            f"\n## 응답 형식",
            f"다음 형식으로 응답해주세요:",
            f"",
            f"```파일명1",
            f"// 파일 내용",
            f"```",
            f"",
            f"```파일명2", 
            f"// 파일 내용",
            f"```",
            f"",
            f"## 구현 설명",
            f"- 간단한 구현 설명을 한글로 작성해주세요",
            f"- 파일별 역할을 설명해주세요",
            f"",
            f"## 주의사항",
            f"- 실제 동작하는 완전한 코드를 작성해주세요",
            f"- 에러 처리를 포함해주세요", 
            f"- 코드 주석은 한글로 작성해주세요",
            f"- 보안과 성능을 고려해주세요"
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_generated_code(self, generated_code: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        생성된 코드를 파일별로 분리합니다.
        
        Args:
            generated_code: Gemini가 생성한 코드
            analysis: 이슈 분석 결과
            
        Returns:
            파싱된 파일 정보
        """
        try:
            files = []
            
            # 코드 블록 패턴 찾기: ```파일명 ... ```
            code_block_pattern = r'```([^\n]+)\n(.*?)```'
            matches = re.findall(code_block_pattern, generated_code, re.DOTALL)
            
            if not matches:
                # 코드 블록이 없으면 단일 파일로 처리
                language = analysis["programming_language"]
                extension_map = {
                    "python": ".py",
                    "javascript": ".js", 
                    "typescript": ".ts",
                    "java": ".java",
                    "go": ".go"
                }
                ext = extension_map.get(language, ".txt")
                
                files.append({
                    "filename": f"solution{ext}",
                    "content": generated_code.strip(),
                    "language": language
                })
            else:
                for filename, content in matches:
                    filename = filename.strip()
                    # 언어 식별자 제거 (예: python, javascript 등)
                    if filename in ["python", "javascript", "typescript", "java", "go"]:
                        language = analysis["programming_language"] 
                        ext = {
                            "python": ".py",
                            "javascript": ".js",
                            "typescript": ".ts", 
                            "java": ".java",
                            "go": ".go"
                        }.get(language, ".txt")
                        filename = f"solution{ext}"
                    
                    files.append({
                        "filename": filename,
                        "content": content.strip(),
                        "language": self._detect_language_from_filename(filename)
                    })
            
            return {
                "success": True,
                "files": files
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"코드 파싱 오류: {str(e)}"
            }
    
    def _detect_language_from_filename(self, filename: str) -> str:
        """파일명에서 프로그래밍 언어를 추정합니다."""
        ext = os.path.splitext(filename)[1].lower()
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript", 
            ".java": "java",
            ".go": "go",
            ".cpp": "cpp",
            ".c": "c"
        }
        return ext_map.get(ext, "text")
    
    def _save_generated_files(self, files: list) -> Dict[str, Any]:
        """
        생성된 파일들을 실제로 저장합니다.
        
        Args:
            files: 저장할 파일 정보 리스트
            
        Returns:
            저장 결과
        """
        try:
            saved_files = []
            
            for file_info in files:
                filename = file_info["filename"]
                content = file_info["content"]
                
                # 파일 경로 보안 검증
                if not self._is_safe_filename(filename):
                    return {
                        "success": False,
                        "error": f"안전하지 않은 파일명입니다: {filename}"
                    }
                
                # 현재 디렉토리에 파일 저장
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    saved_files.append({
                        "filename": filename,
                        "path": os.path.abspath(filename),
                        "size": len(content)
                    })
                    logger.info(f"파일 저장 완료: {filename}")
                    
                except IOError as e:
                    return {
                        "success": False,
                        "error": f"파일 저장 실패 ({filename}): {str(e)}"
                    }
            
            return {
                "success": True,
                "saved_files": saved_files,
                "message": f"{len(saved_files)}개 파일이 저장되었습니다"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"파일 저장 중 오류: {str(e)}"
            }
    
    def _is_safe_filename(self, filename: str) -> bool:
        """파일명이 안전한지 검증합니다."""
        # 경로 순회 공격 방지
        if ".." in filename or filename.startswith("/"):
            return False
        
        # 허용된 문자만 사용
        allowed_chars = string.ascii_letters + string.digits + ".-_"
        if not all(c in allowed_chars for c in filename):
            return False
        
        return True


# 전역 인스턴스
code_generator = None


async def get_code_generator() -> CodeGenerator:
    """코드 생성기 인스턴스를 가져오거나 생성합니다."""
    global code_generator
    if code_generator is None:
        code_generator = CodeGenerator()
    return code_generator