"""Main entry point for the Gemini Review MCP server."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to Python path to import config
sys.path.append(str(Path(__file__).parent.parent))

# Debug: Print startup info
print("=== Gemini Review MCP Server Starting ===", file=sys.stderr)
print(f"Python path: {sys.executable}", file=sys.stderr)
print(f"Working directory: {Path.cwd()}", file=sys.stderr)
print(f"Script path: {Path(__file__).resolve()}", file=sys.stderr)

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
ENHANCE_CODE_TOOL = Tool(
    name="gemini_review",
    description="Enhance code with Gemini AI review and improvement suggestions",
    inputSchema={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The code to enhance"
            },
            "request": {
                "type": "string",
                "description": "Additional enhancement request (optional)",
                "default": ""
            },
            "language": {
                "type": "string",
                "description": "Programming language (optional)",
                "default": "auto-detect"
            },
            "requirements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific requirements or focus areas (optional)",
                "default": ["security", "performance", "best-practices", "readability"]
            }
        },
        "required": ["code"]
    }
)


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools."""
    return [ENHANCE_CODE_TOOL]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        logger.info(f"Tool called: {name} with arguments: {arguments}")
        workflow_manager = await get_workflow_manager()

        if name == "gemini_review":
            # Handle code enhancement request
            code = arguments.get("code", "")
            if not code:
                return [TextContent(
                    type="text",
                    text="❌ **오류:** 개선할 코드가 제공되지 않았습니다"
                )]

            result = await workflow_manager.handle_code_enhancement(
                code=code,
                request=arguments.get("request", ""),
                language=arguments.get("language"),
                requirements=arguments.get("requirements")
            )

            if result["success"]:
                response_parts = [
                    f"⚡ **코드 개선 분석 완료**",
                    f"🆔 워크플로우 ID: {result['workflow_id']}",
                    f"🔤 언어: {result['language']}",
                    f"🚨 크리티컬 이슈: {'있음' if result['has_critical_issues'] else '없음'}",
                    f"💡 개선 권장: {'예' if result['improvement_recommended'] else '아니오'}",
                    ""
                ]

                # Add review information
                stages = result.get('stages', {})
                if 'review' in stages:
                    review_text = stages['review'].get('review', '')
                    response_parts.extend([
                        "🔍 **상세 리뷰:**",
                        review_text
                    ])

                if result.get('improvement_suggestions'):
                    response_parts.extend([
                        "",
                        "💡 **개선 제안:**",
                        result['improvement_suggestions']
                    ])

                return [TextContent(type="text", text="\n".join(response_parts))]
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ **코드 개선 분석 실패:** {result.get('error', '알 수 없는 오류')}"
                )]

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
                capabilities={
                    "tools": {}
                }
            )
        )


if __name__ == "__main__":
    asyncio.run(main())