"""Gemini API client for code review."""

import logging
from typing import Optional, Dict, Any, List
import google.generativeai as genai
from google.generativeai import GenerativeModel
from google.api_core import exceptions

from config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for interacting with Gemini API for code review."""
    
    def __init__(self):
        """Initialize Gemini client with API key from settings."""
        genai.configure(api_key=settings.gemini_api_key)
        self.model_name = settings.gemini_model
        self.fallback_model_name = getattr(settings, 'gemini_model_fallback', 'gemini-2.0-flash-001')
        self.model = GenerativeModel(self.model_name)
        self.fallback_model = GenerativeModel(self.fallback_model_name)
        
    async def review_code(
        self,
        code: str,
        language: Optional[str] = None,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Review code for quality, security, and improvements.
        
        Args:
            code: The code to review
            language: Programming language (optional)
            focus_areas: Specific areas to focus on (optional)
            
        Returns:
            Dict containing review results
        """
        try:
            # Default focus areas if not provided
            if not focus_areas:
                focus_areas = ["security", "performance", "best-practices", "readability"]
            
            # Build the review prompt
            prompt_parts = [
                "당신은 전문 코드 리뷰어입니다. 다음 코드에 대해 철저한 리뷰를 제공해주세요.",
                f"\n프로그래밍 언어: {language if language else '자동 감지'}",
                "\n다음 영역에 집중해주세요:"
            ]
            
            for area in focus_areas:
                prompt_parts.append(f"- {area}")
                
            prompt_parts.extend([
                "\n\nCode to review:",
                f"```{language if language else ''}",
                code,
                "```",
                "\n\n다음 구조로 포괄적인 리뷰를 제공해주세요:",
                "1. **전반적 평가** - 코드 품질에 대한 간략한 요약",
                "2. **강점** - 코드가 잘 구현된 부분",
                "3. **우선순위별 이슈** - 모든 이슈를 우선순위별로 분류:",
                "   - 🔴 **치명적**: 보안 취약점, 데이터 손상 위험, 시스템 크래시",
                "   - 🟡 **높음**: 성능 문제, 유지보수성 문제, 로직 오류", 
                "   - 🟠 **중간**: 코드 스타일 문제, 사소한 비효율성, 누락된 검증",
                "   - 🟢 **낮음**: 문서화, 네이밍 개선, 소소한 최적화",
                "4. **구체적 개선 제안** - 코드 예제와 함께 실행 가능한 권장사항",
                "5. **보안 분석** - 전용 보안 리뷰",
                "6. **성능 고려사항** - 성능 관련 관찰 사항"
            ])
            
            prompt = "\n".join(prompt_parts)
            
            # Try primary model first, fallback if needed
            logger.info(f"Reviewing code with Gemini ({self.model_name})")
            try:
                response = await self._generate_content_async(self.model, prompt)
            except (exceptions.ResourceExhausted, exceptions.ServiceUnavailable) as e:
                logger.warning(f"Primary model {self.model_name} unavailable, using fallback {self.fallback_model_name}")
                response = await self._generate_content_async(self.fallback_model, prompt)
            
            review_text = response.text
            
            # Parse review into structured format
            review_data = self._parse_review(review_text)
            
            return {
                "success": True,
                "review": review_text,
                "structured_review": review_data,
                "language": language or "auto-detected",
                "focus_areas": focus_areas,
                "model": self.model_name,
                "code_length": len(code)
            }
            
        except Exception as e:
            logger.error(f"Error reviewing code: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "code_snippet": code[:200] + "..." if len(code) > 200 else code
            }
    
    async def compare_implementations(
        self,
        original_code: str,
        improved_code: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare original and improved code implementations.
        
        Args:
            original_code: The original code
            improved_code: The improved version
            language: Programming language (optional)
            
        Returns:
            Dict containing comparison results
        """
        try:
            prompt = f"""이 두 코드 구현을 비교하고 개선 사항을 분석해주세요.

원본 코드:
```{language or ''}
{original_code}
```

개선된 코드:
```{language or ''}
{improved_code}
```

다음을 제공해주세요:
1. 변경 사항 요약
2. 각 변경이 리뷰 피드백을 어떻게 해결하는지
3. 남은 문제나 제안 사항
4. 전반적인 개선도 평가 (1-10점 척도)
"""
            
            logger.info(f"Comparing implementations with Gemini ({self.model_name})")
            try:
                response = await self._generate_content_async(self.model, prompt)
            except (exceptions.ResourceExhausted, exceptions.ServiceUnavailable) as e:
                logger.warning(f"Primary model unavailable, using fallback")
                response = await self._generate_content_async(self.fallback_model, prompt)
            
            return {
                "success": True,
                "comparison": response.text,
                "model": self.model_name
            }
            
        except Exception as e:
            logger.error(f"Error comparing implementations: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_improvement_suggestions(
        self,
        code: str,
        review: str,
        language: Optional[str] = None,
        requirements: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate specific improvement suggestions based on code review.
        
        Args:
            code: The original code
            review: The review feedback
            language: Programming language (optional)
            requirements: Additional requirements (optional)
            
        Returns:
            Dict containing improvement suggestions
        """
        try:
            # Build the improvement prompt
            prompt_parts = [
                "당신은 전문 코드 개선 컨설턴트입니다. 제공된 코드 리뷰를 바탕으로 구체적이고 실행 가능한 개선 제안을 생성해주세요.",
                f"\n원본 코드:",
                f"```{language or ''}",
                code,
                "```",
                f"\n코드 리뷰:",
                review,
                "\n다음을 제공해주세요:",
                "1. **우선순위 기반 개선 계획** - 치명적 및 높음 우선순위 이슈에 먼저 집중",
                "2. **구체적 코드 변경** - 수정해야 할 정확한 코드 스니펫",
                "3. **구현 단계** - 개선 사항 적용을 위한 단계별 가이드",
                "4. **검증 방법** - 개선 사항이 올바르게 작동하는지 확인하는 방법"
            ]
            
            if requirements:
                prompt_parts.extend([
                    "\nAdditional Requirements:",
                    *[f"- {req}" for req in requirements]
                ])
                
            prompt_parts.extend([
                "\n명확한 섹션으로 응답을 구성하고 구체적이고 구현 가능한 솔루션을 제공해주세요.",
                "보안, 성능, 유지보수성 문제를 해결하는 가장 영향력 있는 개선 사항에 집중해주세요."
            ])
            
            prompt = "\n".join(prompt_parts)
            
            logger.info(f"Generating improvement suggestions with Gemini ({self.model_name})")
            try:
                response = await self._generate_content_async(self.model, prompt)
            except (exceptions.ResourceExhausted, exceptions.ServiceUnavailable) as e:
                logger.warning(f"Primary model unavailable, using fallback")
                response = await self._generate_content_async(self.fallback_model, prompt)
            
            suggestions_text = response.text
            
            # Parse suggestions into structured format
            suggestions_data = self._parse_improvement_suggestions(suggestions_text)
            
            return {
                "success": True,
                "suggestions": suggestions_text,
                "structured_suggestions": suggestions_data,
                "language": language or "auto-detected",
                "model": self.model_name,
                "based_on_review": True
            }
            
        except Exception as e:
            logger.error(f"Error generating improvement suggestions: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "code_snippet": code[:200] + "..." if len(code) > 200 else code
            }
    
    async def _generate_content_async(self, model: GenerativeModel, prompt: str):
        """
        Generate content using Gemini model asynchronously.
        
        Note: google-generativeai doesn't have native async support yet,
        so we'll use sync method. In production, consider using
        asyncio.to_thread for true async behavior.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, model.generate_content, prompt)
    
    def _parse_review(self, review_text: str) -> Dict[str, Any]:
        """
        Parse review text into structured format.
        
        Args:
            review_text: Raw review text from Gemini
            
        Returns:
            Structured review data
        """
        # Enhanced parsing with priority levels
        sections = {
            "overall_assessment": "",
            "strengths": [],
            "issues_by_priority": {
                "critical": [],
                "high": [],
                "medium": [], 
                "low": []
            },
            "improvements": [],
            "security_concerns": [],
            "performance_notes": []
        }
        
        current_section = None
        lines = review_text.split('\n')
        
        current_priority = None
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if 'overall assessment' in line_lower:
                current_section = 'overall_assessment'
            elif 'strength' in line_lower:
                current_section = 'strengths'
            elif 'issues by priority' in line_lower or 'issue' in line_lower:
                current_section = 'issues'
            elif 'improvement' in line_lower or 'suggestion' in line_lower:
                current_section = 'improvements'
            elif 'security' in line_lower:
                current_section = 'security_concerns'
            elif 'performance' in line_lower:
                current_section = 'performance_notes'
            
            # Check for priority levels in issues section
            if current_section == 'issues':
                if '🔴' in line or 'critical' in line_lower:
                    current_priority = 'critical'
                elif '🟡' in line or 'high' in line_lower:
                    current_priority = 'high'
                elif '🟠' in line or 'medium' in line_lower:
                    current_priority = 'medium'
                elif '🟢' in line or 'low' in line_lower:
                    current_priority = 'low'
                elif current_priority and line.strip() and line.strip().startswith(('-', '*', '•')):
                    sections["issues_by_priority"][current_priority].append(line.strip())
            
            elif current_section and line.strip():
                if current_section == 'overall_assessment':
                    sections[current_section] += line + '\n'
                elif line.strip().startswith(('-', '*', '•', '1.', '2.', '3.')):
                    sections[current_section].append(line.strip())
        
        return sections
    
    def _parse_improvement_suggestions(self, suggestions_text: str) -> Dict[str, Any]:
        """
        Parse improvement suggestions text into structured format.
        
        Args:
            suggestions_text: Raw suggestions text from Gemini
            
        Returns:
            Structured suggestions data
        """
        sections = {
            "priority_plan": [],
            "code_changes": [],
            "implementation_steps": [],
            "validation_methods": [],
            "summary": ""
        }
        
        current_section = None
        lines = suggestions_text.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if 'priority' in line_lower and 'plan' in line_lower:
                current_section = 'priority_plan'
            elif 'code changes' in line_lower or 'specific' in line_lower:
                current_section = 'code_changes'
            elif 'implementation' in line_lower and 'steps' in line_lower:
                current_section = 'implementation_steps'
            elif 'validation' in line_lower or 'verify' in line_lower:
                current_section = 'validation_methods'
            elif 'summary' in line_lower:
                current_section = 'summary'
            
            elif current_section and line.strip():
                if current_section == 'summary':
                    sections[current_section] += line + '\n'
                elif line.strip().startswith(('-', '*', '•', '1.', '2.', '3.')):
                    sections[current_section].append(line.strip())
        
        return sections


# Global client instance
gemini_client = None


async def get_gemini_client() -> GeminiClient:
    """Get or create Gemini client instance."""
    global gemini_client
    if gemini_client is None:
        gemini_client = GeminiClient()
    return gemini_client