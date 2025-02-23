import io

from PIL import Image as PILImage
from loguru import logger
import logfire
from mcp.server.fastmcp import Image

from basic_memory.mcp.server import mcp
from basic_memory.mcp.async_client import client
from basic_memory.mcp.tools.utils import call_get
from basic_memory.schemas.memory import memory_url_path

import base64


@mcp.tool(description="Read a single file's content by path or permalink")
async def read_resource(path: str) -> dict:
    """Get a file's raw content.
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
        # images are returned as "image"
        elif content_type.startswith("image/"):
            # Load image using PIL 
            img = PILImage.open(io.BytesIO(response.content))

            # Convert to RGB if needed (in case it's RGBA/PNG)
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGB')

            # Check if resize needed
            max_size = 800
            if img.width > max_size or img.height > max_size:
                # Calculate new size maintaining aspect ratio
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, PILImage.Resampling.LANCZOS)

            # Save as JPEG to bytes buffer with reduced quality
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=70, optimize=True)
            img_bytes = buf.getvalue()

            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(img_bytes).decode("utf-8")
                }
            }
        # Other types, like pdf are returned as "document"
        else:             
            return {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": content_type,
                    "data": base64.b64encode(response.content).decode("utf-8"),
                },
            }