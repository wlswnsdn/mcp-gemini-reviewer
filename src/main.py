"""Main entry point for the Gemini Review MCP server."""

import asyncio
import json
import logging
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
import mcp.server.stdio

from config import settings

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
        
        if name == "request_code_implementation":
            # TODO: Implement in step 6
            result = f"Code implementation requested: {arguments.get('request')}"
            
        elif name == "review_code_with_gemini":
            # TODO: Implement in step 6  
            result = f"Code review requested for: {arguments.get('language', 'auto-detect')} code"
            
        elif name == "improve_code_with_feedback":
            # TODO: Implement in step 6
            result = "Code improvement requested based on feedback"
            
        elif name == "get_review_history":
            # TODO: Implement in step 6
            result = f"Review history requested (limit: {arguments.get('limit', 10)})"
            
        else:
            result = f"Unknown tool: {name}"
            
        return [TextContent(type="text", text=result)]
        
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}")
        return [TextContent(
            type="text", 
            text=f"Error executing tool {name}: {str(e)}"
        )]


@app.initialization_options()
async def get_initialization_options() -> InitializationOptions:
    """Return server initialization options."""
    return InitializationOptions(
        server_name=settings.mcp_server_name,
        server_version=settings.mcp_server_version,
        capabilities={}
    )


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
                server_version=settings.mcp_server_version
            )
        )


if __name__ == "__main__":
    asyncio.run(main())