"""Main entry point for the Gemini Review MCP server."""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to Python path to import config
sys.path.append(str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
import mcp.server.stdio

from config import settings
from workflow import get_workflow_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create MCP server instance
app = Server(settings.mcp_server_name)


# Define tools
REQUEST_CODE_TOOL = Tool(
    name="request_code_implementation",
    description="Request Claude to implement code based on user requirements",
    inputSchema={
        "type": "object",
        "properties": {
            "request": {
                "type": "string",
                "description": "The code implementation request"
            },
            "language": {
                "type": "string", 
                "description": "Programming language (optional)",
                "default": "auto-detect"
            },
            "requirements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of specific requirements (optional)"
            }
        },
        "required": ["request"]
    }
)

REVIEW_CODE_TOOL = Tool(
    name="review_code_with_gemini",
    description="Review code using Gemini AI for quality, security, and improvements",
    inputSchema={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The code to review"
            },
            "language": {
                "type": "string",
                "description": "Programming language",
                "default": "auto-detect"
            },
            "focus_areas": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific areas to focus on (e.g., security, performance)",
                "default": ["security", "performance", "best-practices", "readability"]
            }
        },
        "required": ["code"]
    }
)

IMPROVE_CODE_TOOL = Tool(
    name="improve_code_with_feedback", 
    description="Improve code based on review feedback",
    inputSchema={
        "type": "object",
        "properties": {
            "original_code": {
                "type": "string",
                "description": "The original code"
            },
            "feedback": {
                "type": "string",
                "description": "Review feedback to address"
            },
            "language": {
                "type": "string",
                "description": "Programming language",
                "default": "auto-detect"
            }
        },
        "required": ["original_code", "feedback"]
    }
)

GET_HISTORY_TOOL = Tool(
    name="get_review_history",
    description="Get the history of code reviews and improvements",
    inputSchema={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of recent entries to retrieve",
                "default": 10
            }
        }
    }
)


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools."""
    return [
        REQUEST_CODE_TOOL,
        REVIEW_CODE_TOOL,
        IMPROVE_CODE_TOOL,
        GET_HISTORY_TOOL
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        logger.info(f"Tool called: {name} with arguments: {arguments}")
        workflow_manager = await get_workflow_manager()
        
        if name == "request_code_implementation":
            # Handle code implementation request
            result = await workflow_manager.handle_implementation_request(
                request=arguments.get("request", ""),
                language=arguments.get("language"),
                requirements=arguments.get("requirements")
            )
            
            if result["success"]:
                response_parts = [
                    f"✅ **코드 구현 완료**",
                    f"🆔 워크플로우 ID: {result['workflow_id']}",
                    f"🔤 언어: {result['language']}",
                    "",
                    "📝 **최종 코드:**",
                    "```" + result['language'],
                    result['final_code'],
                    "```"
                ]
                
                # Add stage information
                stages = result.get('stages', {})
                if 'review' in stages:
                    response_parts.extend([
                        "",
                        "🔍 **리뷰 요약:**",
                        stages['review'].get('review', '리뷰 세부사항이 없습니다')[:500] + "..."
                    ])
                
                if 'improvement' in stages:
                    response_parts.extend([
                        "",
                        "⚡ **리뷰 피드백을 바탕으로 코드가 개선되었습니다**"
                    ])
                
                return [TextContent(type="text", text="\n".join(response_parts))]
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ **코드 구현 실패:** {result.get('error', '알 수 없는 오류')}"
                )]
            
        elif name == "review_code_with_gemini":
            # Handle direct code review
            code = arguments.get("code", "")
            if not code:
                return [TextContent(
                    type="text",
                    text="❌ **오류:** 리뷰할 코드가 제공되지 않았습니다"
                )]
            
            # Use workflow manager to handle review
            from gemini_client import get_gemini_client
            gemini_client = await get_gemini_client()
            
            review_result = await gemini_client.review_code(
                code=code,
                language=arguments.get("language"),
                focus_areas=arguments.get("focus_areas")
            )
            
            if review_result["success"]:
                response_parts = [
                    f"🔍 **코드 리뷰 완료**",
                    f"🔤 언어: {review_result['language']}",
                    f"📏 코드 길이: {review_result['code_length']}자",
                    "",
                    "📋 **리뷰 결과:**",
                    review_result['review']
                ]
                
                return [TextContent(type="text", text="\n".join(response_parts))]
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ **리뷰 실패:** {review_result.get('error', '알 수 없는 오류')}"
                )]
            
        elif name == "improve_code_with_feedback":
            # Handle code improvement
            original_code = arguments.get("original_code", "")
            feedback = arguments.get("feedback", "")
            
            if not original_code or not feedback:
                return [TextContent(
                    type="text",
                    text="❌ **오류:** 원본 코드와 피드백이 모두 필요합니다"
                )]
            
            # TODO: Implement improvement logic with Gemini
            return [TextContent(
                type="text",
                text="❌ **코드 개선 기능:** 현재 재구현 중입니다. Gemini 리뷰 기능을 사용해주세요."
            )]
            
        elif name == "get_review_history":
            # Get review history
            limit = arguments.get("limit", 10)
            history = workflow_manager.get_history(limit)
            
            if not history:
                return [TextContent(
                    type="text",
                    text="📊 **리뷰 히스토리:** 기록이 없습니다"
                )]
            
            response_parts = [f"📊 **리뷰 히스토리 (최근 {len(history)}개 항목):**", ""]
            
            for i, entry in enumerate(reversed(history), 1):
                status = "✅" if entry['success'] else "❌"
                response_parts.append(
                    f"{i}. {status} [{entry['timestamp'][:19]}] "
                    f"{entry.get('language', '알 수 없음')} - {entry['request'][:50]}..."
                )
            
            return [TextContent(type="text", text="\n".join(response_parts))]
            
        else:
            return [TextContent(
                type="text",
                text=f"❌ **알 수 없는 도구:** {name}"
            )]
            
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}")
        return [TextContent(
            type="text", 
            text=f"❌ **도구 실행 오류 {name}:** {str(e)}"
        )]


async def main():
    """Run the MCP server."""
    logger.info(f"Starting {settings.mcp_server_name} v{settings.mcp_server_version}")
    
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=settings.mcp_server_name,
                server_version=settings.mcp_server_version,
                capabilities={}
            )
        )


if __name__ == "__main__":
    asyncio.run(main())