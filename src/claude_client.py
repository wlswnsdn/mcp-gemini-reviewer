"""Claude API client for code generation."""

import logging
from typing import Optional, Dict, Any, List
import anthropic
from anthropic import AsyncAnthropic

from config import settings

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for interacting with Claude API."""
    
    def __init__(self):
        """Initialize Claude client with API key from settings."""
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
        
    async def generate_code(
        self,
        request: str,
        language: Optional[str] = None,
        requirements: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate code based on user request.
        
        Args:
            request: The code implementation request
            language: Programming language (optional)
            requirements: List of specific requirements (optional)
            
        Returns:
            Dict containing generated code and metadata
        """
        try:
            # Build the prompt
            prompt_parts = [
                "You are an expert software developer. Generate clean, efficient, and well-documented code based on the following request."
            ]
            
            prompt_parts.append(f"\nRequest: {request}")
            
            if language and language != "auto-detect":
                prompt_parts.append(f"\nProgramming Language: {language}")
                
            if requirements:
                prompt_parts.append("\nSpecific Requirements:")
                for req in requirements:
                    prompt_parts.append(f"- {req}")
                    
            prompt_parts.append("\nPlease provide the complete implementation with clear comments explaining the code.")
            
            prompt = "\n".join(prompt_parts)
            
            # Call Claude API
            logger.info(f"Generating code with Claude ({self.model})")
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract the generated code
            generated_content = response.content[0].text
            
            # Try to detect language if not specified
            detected_language = self._detect_language(generated_content) if not language else language
            
            return {
                "success": True,
                "code": generated_content,
                "language": detected_language,
                "model": self.model,
                "request": request,
                "requirements": requirements or []
            }
            
        except Exception as e:
            logger.error(f"Error generating code: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "request": request
            }
    
    async def improve_code(
        self,
        original_code: str,
        feedback: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Improve code based on review feedback.
        
        Args:
            original_code: The original code to improve
            feedback: Review feedback to address
            language: Programming language (optional)
            
        Returns:
            Dict containing improved code and metadata
        """
        try:
            prompt = f"""You are an expert software developer. Improve the following code based on the review feedback provided.

Original Code:
```{language or ''}
{original_code}
```

Review Feedback:
{feedback}

Please provide the improved code that addresses all the feedback points while maintaining the original functionality.
Explain the key changes you made."""

            logger.info(f"Improving code with Claude ({self.model})")
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            improved_content = response.content[0].text
            
            return {
                "success": True,
                "improved_code": improved_content,
                "original_code": original_code,
                "feedback_addressed": feedback,
                "language": language or self._detect_language(improved_content),
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"Error improving code: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "original_code": original_code,
                "feedback": feedback
            }
    
    def _detect_language(self, code: str) -> str:
        """
        Simple language detection based on code patterns.
        
        Args:
            code: The code to analyze
            
        Returns:
            Detected language or 'unknown'
        """
        # Simple heuristic-based detection
        code_lower = code.lower()
        
        if "```python" in code_lower or "import " in code or "def " in code:
            return "python"
        elif "```javascript" in code_lower or "function " in code or "const " in code:
            return "javascript"
        elif "```typescript" in code_lower or "interface " in code or ": string" in code:
            return "typescript"
        elif "```java" in code_lower or "public class" in code or "public static void" in code:
            return "java"
        elif "```go" in code_lower or "package main" in code or "func " in code:
            return "go"
        elif "```rust" in code_lower or "fn main()" in code or "let mut" in code:
            return "rust"
        elif "```cpp" in code_lower or "```c++" in code_lower or "#include <" in code:
            return "cpp"
        else:
            return "unknown"


# Global client instance
claude_client = None


async def get_claude_client() -> ClaudeClient:
    """Get or create Claude client instance."""
    global claude_client
    if claude_client is None:
        claude_client = ClaudeClient()
    return claude_client