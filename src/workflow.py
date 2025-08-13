"""Workflow manager for coordinating Gemini-based code review and enhancement process."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import re

from gemini_client import get_gemini_client
from config import settings

logger = logging.getLogger(__name__)


class WorkflowManager:
    """Manages the workflow for Gemini-based code review and enhancement."""
    
    def __init__(self):
        """Initialize workflow manager."""
        self.history: List[Dict[str, Any]] = []
        
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
            # For implementation, we expect the user to provide code to enhance
            return {
                "success": False,
                "message": "Implementation requests now require providing existing code for enhancement. Please use the enhance_code_with_review tool with your code.",
                "intent": intent
            }
        elif intent == "review":
            return await self.handle_review_request(user_message)
        else:
            # General question/explanation - not handled by this MCP server
            return {
                "success": False,
                "message": "This request doesn't require code implementation or review. Please use Claude directly for general questions.",
                "intent": intent
            }
    
    async def handle_code_enhancement(
        self,
        code: str,
        request: str = "",
        language: Optional[str] = None,
        requirements: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Handle code enhancement with Gemini review and improvement suggestions.
        
        Args:
            code: The code to enhance
            request: Additional enhancement request (optional)
            language: Programming language (optional)
            requirements: Specific requirements (optional)
            
        Returns:
            Enhancement result with review and suggestions
        """
        workflow_id = self._generate_workflow_id()
        result = {
            "workflow_id": workflow_id,
            "original_code": code,
            "request": request,
            "stages": {}
        }
        
        try:
            # Stage 1: Review code with Gemini
            logger.info("Stage 1: Reviewing code with Gemini")
            gemini_client = await get_gemini_client()
            
            # Prepare focus areas based on requirements
            focus_areas = requirements if requirements else ["security", "performance", "best-practices", "readability"]
            
            review_result = await gemini_client.review_code(
                code=code,
                language=language,
                focus_areas=focus_areas
            )
            
            if not review_result["success"]:
                result["success"] = False
                result["error"] = f"Code review failed: {review_result.get('error')}"
                return result
                
            result["stages"]["review"] = review_result
            detected_language = review_result.get("language", language or "unknown")
            
            # Stage 2: Mark if improvement suggestions are recommended
            if self._has_significant_issues(review_result):
                logger.info("Stage 2: Significant issues found - improvement recommended")
                result["improvement_suggestions"] = "Based on the review, consider addressing the CRITICAL and HIGH priority issues identified."
            
            # Prepare final result
            result["success"] = True
            result["language"] = detected_language
            result["has_critical_issues"] = self._has_critical_issues(review_result)
            result["improvement_recommended"] = self._has_significant_issues(review_result)
            
            # Store in history
            self._add_to_history(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Enhancement workflow error: {str(e)}")
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
        
        # Check structured review for priority issues
        structured_review = review_result.get("structured_review", {})
        issues_by_priority = structured_review.get("issues_by_priority", {})
        
        # Consider CRITICAL and HIGH priority issues as significant
        critical_issues = issues_by_priority.get("critical", [])
        high_issues = issues_by_priority.get("high", [])
        
        if critical_issues or high_issues:
            return True
        
        # Fallback to text-based detection if structured parsing failed
        review_text = review_result.get("review", "").lower()
        
        # Keywords indicating significant issues
        critical_keywords = [
            "🔴", "critical", "security", "vulnerability", "unsafe", "injection",
            "crash", "corruption", "data loss"
        ]
        high_keywords = [
            "🟡", "high", "performance", "error", "bug", "logic error",
            "maintainability"
        ]
        
        return any(keyword in review_text for keyword in critical_keywords + high_keywords)
    
    def _has_critical_issues(self, review_result: Dict[str, Any]) -> bool:
        """Check if review found critical issues."""
        if not review_result.get("success"):
            return False
        
        # Check structured review for critical issues
        structured_review = review_result.get("structured_review", {})
        issues_by_priority = structured_review.get("issues_by_priority", {})
        
        # Check for CRITICAL priority issues
        critical_issues = issues_by_priority.get("critical", [])
        if critical_issues:
            return True
        
        # Fallback to text-based detection
        review_text = review_result.get("review", "").lower()
        critical_keywords = [
            "🔴", "critical", "security", "vulnerability", "unsafe", "injection",
            "crash", "corruption", "data loss"
        ]
        
        return any(keyword in review_text for keyword in critical_keywords)
    
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