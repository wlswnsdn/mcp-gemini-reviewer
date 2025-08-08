"""Workflow manager for coordinating code implementation and review process."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import re

from claude_client import get_claude_client
from gemini_client import get_gemini_client
from config import settings

logger = logging.getLogger(__name__)


class WorkflowManager:
    """Manages the workflow between Claude code generation and Gemini review."""
    
    def __init__(self):
        """Initialize workflow manager."""
        self.history: List[Dict[str, Any]] = []
        self.auto_review = settings.auto_review
        self.auto_improve = settings.auto_improve
        
    async def process_request(
        self,
        user_message: str,
        force_implementation: bool = False
    ) -> Dict[str, Any]:
        """
        Process user request and determine appropriate action.
        
        Args:
            user_message: The user's message
            force_implementation: Force code implementation regardless of intent
            
        Returns:
            Result of the appropriate action
        """
        # Determine user intent
        intent = self._analyze_intent(user_message) if not force_implementation else "implementation"
        
        logger.info(f"Detected intent: {intent}")
        
        if intent == "implementation":
            return await self.handle_implementation_request(user_message)
        elif intent == "review":
            return await self.handle_review_request(user_message)
        else:
            # General question/explanation - not handled by this MCP server
            return {
                "success": False,
                "message": "This request doesn't require code implementation or review. Please use Claude directly for general questions.",
                "intent": intent
            }
    
    async def handle_implementation_request(
        self,
        request: str,
        language: Optional[str] = None,
        requirements: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Handle code implementation request with automatic review and improvement.
        
        Args:
            request: The implementation request
            language: Programming language (optional)
            requirements: Specific requirements (optional)
            
        Returns:
            Complete workflow result
        """
        workflow_id = self._generate_workflow_id()
        result = {
            "workflow_id": workflow_id,
            "request": request,
            "stages": {}
        }
        
        try:
            # Stage 1: Generate code with Claude
            logger.info("Stage 1: Generating code with Claude")
            claude_client = await get_claude_client()
            generation_result = await claude_client.generate_code(
                request=request,
                language=language,
                requirements=requirements
            )
            
            if not generation_result["success"]:
                result["success"] = False
                result["error"] = f"Code generation failed: {generation_result.get('error')}"
                return result
                
            result["stages"]["generation"] = generation_result
            generated_code = generation_result["code"]
            detected_language = generation_result.get("language", "unknown")
            
            # Stage 2: Review with Gemini (if auto_review is enabled)
            if self.auto_review:
                logger.info("Stage 2: Reviewing code with Gemini")
                gemini_client = await get_gemini_client()
                review_result = await gemini_client.review_code(
                    code=generated_code,
                    language=detected_language
                )
                
                if not review_result["success"]:
                    logger.warning(f"Review failed: {review_result.get('error')}")
                    result["stages"]["review"] = review_result
                else:
                    result["stages"]["review"] = review_result
                    
                    # Stage 3: Improve based on feedback (if auto_improve is enabled)
                    if self.auto_improve and self._has_significant_issues(review_result):
                        logger.info("Stage 3: Improving code based on feedback")
                        improvement_result = await claude_client.improve_code(
                            original_code=generated_code,
                            feedback=review_result["review"],
                            language=detected_language
                        )
                        
                        if improvement_result["success"]:
                            result["stages"]["improvement"] = improvement_result
                            
                            # Stage 4: Final review of improved code
                            logger.info("Stage 4: Final review of improved code")
                            final_review = await gemini_client.compare_implementations(
                                original_code=generated_code,
                                improved_code=improvement_result["improved_code"],
                                language=detected_language
                            )
                            result["stages"]["final_review"] = final_review
            
            # Prepare final result
            result["success"] = True
            result["final_code"] = result["stages"].get("improvement", {}).get("improved_code", generated_code)
            result["language"] = detected_language
            
            # Store in history
            self._add_to_history(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Workflow error: {str(e)}")
            result["success"] = False
            result["error"] = str(e)
            return result
    
    async def handle_review_request(self, message: str) -> Dict[str, Any]:
        """
        Handle direct code review request.
        
        Args:
            message: Message containing code to review
            
        Returns:
            Review result
        """
        # Extract code from message
        code = self._extract_code_from_message(message)
        if not code:
            return {
                "success": False,
                "error": "No code found in the message. Please include code to review."
            }
        
        # Detect language
        language = self._detect_language_from_message(message)
        
        # Review with Gemini
        gemini_client = await get_gemini_client()
        review_result = await gemini_client.review_code(
            code=code,
            language=language
        )
        
        return review_result
    
    def _analyze_intent(self, message: str) -> str:
        """
        Analyze user message to determine intent.
        
        Args:
            message: User message
            
        Returns:
            Intent type: 'implementation', 'review', or 'question'
        """
        message_lower = message.lower()
        
        # Implementation keywords
        implementation_keywords = [
            "구현", "생성", "만들어", "작성", "개발", "빌드", "생성해", "만들어줘", "코드 작성", "api"
        ]
        
        # Review keywords
        review_keywords = [
            "리뷰", "검토", "확인", "분석", "평가", "체크", "검사", "피드백", "검증"
        ]
        
        # Question keywords
        question_keywords = [
            "무엇", "설명", "알려줘", "어떻게", "왜", "궁금", "질문", "의문"
        ]
        
        # Check for code blocks in message (indicates review request)
        if "```" in message or re.search(r'(def |class |function |import |const |let |var )', message):
            if any(keyword in message_lower for keyword in review_keywords):
                return "review"
        
        # Check implementation intent
        if any(keyword in message_lower for keyword in implementation_keywords):
            return "implementation"
            
        # Check review intent
        if any(keyword in message_lower for keyword in review_keywords):
            return "review"
            
        # Default to question
        return "question"
    
    def _extract_code_from_message(self, message: str) -> Optional[str]:
        """Extract code from message."""
        # Look for code blocks
        code_block_match = re.search(r'```[\w]*\n(.*?)\n```', message, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1)
        
        # Look for indented code
        lines = message.split('\n')
        code_lines = []
        for line in lines:
            if line.startswith('    ') or line.startswith('\t'):
                code_lines.append(line)
        
        if code_lines:
            return '\n'.join(code_lines)
        
        return None
    
    def _detect_language_from_message(self, message: str) -> Optional[str]:
        """Detect programming language from message."""
        # Check for language in code block
        code_block_match = re.search(r'```(\w+)\n', message)
        if code_block_match:
            return code_block_match.group(1)
        
        # Check for language mentions
        languages = ["python", "javascript", "typescript", "java", "go", "rust", "cpp", "c++"]
        message_lower = message.lower()
        for lang in languages:
            if lang in message_lower:
                return lang
        
        return None
    
    def _has_significant_issues(self, review_result: Dict[str, Any]) -> bool:
        """Check if review found significant issues worth improving."""
        if not review_result.get("success"):
            return False
            
        review_text = review_result.get("review", "").lower()
        
        # Keywords indicating significant issues
        issue_keywords = [
            "security", "vulnerability", "unsafe", "injection",
            "error", "bug", "issue", "problem", "incorrect",
            "improve", "better", "optimize", "refactor"
        ]
        
        return any(keyword in review_text for keyword in issue_keywords)
    
    def _generate_workflow_id(self) -> str:
        """Generate unique workflow ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"workflow_{timestamp}"
    
    def _add_to_history(self, result: Dict[str, Any]):
        """Add workflow result to history."""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "workflow_id": result.get("workflow_id"),
            "request": result.get("request"),
            "success": result.get("success"),
            "language": result.get("language")
        })
        
        # Keep only last 100 entries
        if len(self.history) > 100:
            self.history = self.history[-100:]
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get workflow history."""
        return self.history[-limit:]


# Global workflow manager instance
workflow_manager = None


async def get_workflow_manager() -> WorkflowManager:
    """Get or create workflow manager instance."""
    global workflow_manager
    if workflow_manager is None:
        workflow_manager = WorkflowManager()
    return workflow_manager