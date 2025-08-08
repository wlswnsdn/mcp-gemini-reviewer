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
                "You are an expert code reviewer. Please provide a thorough review of the following code.",
                f"\nProgramming Language: {language if language else 'auto-detect'}",
                "\nFocus on the following areas:"
            ]
            
            for area in focus_areas:
                prompt_parts.append(f"- {area}")
                
            prompt_parts.extend([
                "\n\nCode to review:",
                f"```{language if language else ''}",
                code,
                "```",
                "\n\nPlease provide a comprehensive review with the following structure:",
                "1. **Overall Assessment** - Brief summary of code quality",
                "2. **Strengths** - What the code does well",
                "3. **Issues by Priority** - Categorize all issues with priority levels:",
                "   - 🔴 **CRITICAL**: Security vulnerabilities, data corruption risks, system crashes",
                "   - 🟡 **HIGH**: Performance issues, maintainability problems, logic errors", 
                "   - 🟠 **MEDIUM**: Code style issues, minor inefficiencies, missing validations",
                "   - 🟢 **LOW**: Documentation, naming improvements, minor optimizations",
                "4. **Specific Improvement Suggestions** - Actionable recommendations with code examples",
                "5. **Security Analysis** - Dedicated security review",
                "6. **Performance Considerations** - Performance-related observations"
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
            prompt = f"""Compare these two code implementations and analyze the improvements made.

Original Code:
```{language or ''}
{original_code}
```

Improved Code:
```{language or ''}
{improved_code}
```

Please provide:
1. Summary of changes made
2. How each change addresses the review feedback
3. Any remaining issues or suggestions
4. Overall improvement assessment (1-10 scale)
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


# Global client instance
gemini_client = None


async def get_gemini_client() -> GeminiClient:
    """Get or create Gemini client instance."""
    global gemini_client
    if gemini_client is None:
        gemini_client = GeminiClient()
    return gemini_client