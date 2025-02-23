from loguru import logger
import logfire

from basic_memory.mcp.server import mcp
from basic_memory.mcp.async_client import client
from basic_memory.mcp.tools.utils import call_get
from basic_memory.schemas.memory import memory_url_path

import base64


@mcp.tool(description="Read a single file's content by path or permalink")
async def read_resource(path: str) -> dict:
    """Get a file's raw content.

    Args:
        path: File path or permalink

    Returns:
        Dict containing:
        - content: File content (base64 encoded for binary files)
        - content_type: MIME type of the file
        - encoding: 'base64' for binary files, 'utf-8' for text

    Examples:
        # Read a PDF
        result = await read_file("docs/example.pdf")
        # Returns: {
        #   "content": "<base64 encoded content>",
        #   "content_type": "application/pdf",
        #   "encoding": "base64"
        # }

        # Read a text file
        result = await read_file("docs/example.txt")
        # Returns: {
        #   "content": "file content as text",
        #   "content_type": "text/plain",
        #   "encoding": "utf-8"
        # }
    """
    with logfire.span("Reading resource", path=path):
        logger.info(f"Reading resource {path}")
        url = memory_url_path(path)
        response = await call_get(client, f"/resource/{url}")

        content_type = response.headers.get("content-type", "application/octet-stream")

        # return text or json as text type
        if content_type.startswith("text/") or content_type == "application/json":
            return {
                "type": "text",
                "text": response.text,
                "content_type": content_type,
                "encoding": "utf-8",
            }
        # images are returned as "image". Other types, like pdf are returned as "document"
        else:
            is_image = content_type.startswith("image/")
            return {
                "type": "image" if is_image else "document",
                "source": {
                    "type": "base64",
                    "media_type": content_type,
                    "data": base64.b64encode(response.content).decode("utf-8"),
                },
            }
