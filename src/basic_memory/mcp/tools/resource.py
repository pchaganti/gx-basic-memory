from loguru import logger
import logfire

from basic_memory.mcp.server import mcp
from basic_memory.mcp.async_client import client
from basic_memory.mcp.tools.utils import call_get
from basic_memory.schemas.memory import memory_url_path

import base64
import io
from PIL import Image as PILImage

def resize_image(img, max_size):
    """Resize image maintaining aspect ratio"""
    if img.width > max_size or img.height > max_size:
        logger.info(f"Image needs resize. Current: {img.width}x{img.height}, Target: {max_size}")
        ratio = min(max_size / img.width, max_size / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        logger.info(f"New size will be: {new_size}")
        return img.resize(new_size, PILImage.Resampling.LANCZOS)
    logger.info(f"No resize needed. Current: {img.width}x{img.height}")
    return img

def optimize_image(img, max_output_bytes=500000):  # 500KB limit
    """Iteratively optimize image until it's under max_output_bytes"""
    logger.info(f"Starting image optimization. Original size: {img.width}x{img.height}, mode: {img.mode}")
    
    # Convert to RGB if needed
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        img = img.convert('RGB')
        logger.info("Converted to RGB mode")
    
    quality = 30
    size = 400
    
    while True:
        logger.info(f"Trying optimization with size={size}, quality={quality}")
        # Try current settings
        buf = io.BytesIO()
        resized = resize_image(img, size)
        logger.info(f"Resized to: {resized.width}x{resized.height}")
        
        resized.save(buf, format='JPEG',
                    quality=quality,
                    optimize=True,
                    progressive=True,
                    subsampling='4:2:0')
        
        output_size = buf.getbuffer().nbytes
        logger.info(f"Output size: {output_size} bytes")
        
        if output_size < max_output_bytes:
            logger.info("Size acceptable, returning image")
            return buf.getvalue()
            
        # Try lower quality first
        if quality > 10:
            quality -= 10
            logger.info(f"Output too big. Reducing quality to {quality}")
        # Then reduce size if quality is already minimum
        elif size > 200:
            size -= 50
            logger.info(f"Output too big. Reducing size to {size}")
        else:
            # If we get here, return the smallest possible version
            logger.info("Reached minimum size/quality, returning anyway")
            return buf.getvalue()

@mcp.tool(description="Read a single file's content by path or permalink")
async def read_resource(path: str) -> dict:
    """Get a file's raw content."""
    with logfire.span("Reading resource", path=path):
        logger.info(f"Reading resource {path}")
        url = memory_url_path(path)
        response = await call_get(client, f"/resource/{url}")

        content_type = response.headers.get("content-type", "application/octet-stream")
        logger.info(f"Resource content type: {content_type}")

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
            logger.info("Processing image...")
            # Load image using PIL
            img = PILImage.open(io.BytesIO(response.content))
            logger.info(f"Loaded image: {img.width}x{img.height} {img.mode}")
            
            # Optimize image
            img_bytes = optimize_image(img)
            logger.info(f"Optimization complete, final size: {len(img_bytes)} bytes")

            result = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(img_bytes).decode("utf-8")
                }
            }
            logger.info("Returning image result")
            return result
            
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
