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
        ratio = min(max_size / img.width, max_size / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        logger.debug("Resizing image", original={
            "width": img.width, 
            "height": img.height
        }, target=new_size)
        return img.resize(new_size, PILImage.Resampling.LANCZOS)
    return img

def optimize_image(img, max_output_bytes=500000):  # 500KB limit
    """Iteratively optimize image until it's under max_output_bytes"""
    logger.debug("Starting optimization", 
                dimensions={"width": img.width, "height": img.height}, 
                mode=img.mode,
                max_bytes=max_output_bytes)
    
    # Convert to RGB if needed
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        img = img.convert('RGB')
        logger.debug("Converted image to RGB")
    
    quality = 30
    size = 400
    
    while True:
        # Try current settings
        buf = io.BytesIO()
        resized = resize_image(img, size)
        
        resized.save(buf, format='JPEG',
                    quality=quality,
                    optimize=True,
                    progressive=True,
                    subsampling='4:2:0')
        
        output_size = buf.getbuffer().nbytes
        logger.debug("Optimization attempt", quality=quality, size=size, output_bytes=output_size)
        
        if output_size < max_output_bytes:
            logger.info("Image optimization complete", 
                      final_size=output_size,
                      quality=quality,
                      dimensions={"width": resized.width, "height": resized.height})
            return buf.getvalue()
            
        # Try lower quality first
        if quality > 10:
            quality -= 10
            logger.debug("Reducing quality", new_quality=quality)
        # Then reduce size if quality is already minimum
        elif size > 200:
            size -= 50
            logger.debug("Reducing size", new_size=size)
        else:
            logger.warning("Reached minimum optimization parameters", 
                         final_size=output_size,
                         over_limit_by=output_size - max_output_bytes)
            return buf.getvalue()

@mcp.tool(description="Read a single file's content by path or permalink")
async def read_resource(path: str) -> dict:
    """Get a file's raw content."""
    logger.info("Reading resource", path=path)
    
    url = memory_url_path(path)
    response = await call_get(client, f"/resource/{url}")
    content_type = response.headers.get("content-type", "application/octet-stream")
    content_length = int(response.headers.get("content-length", 0))
    
    logger.debug("Resource metadata", 
                content_type=content_type,
                size=content_length,
                path=path)

    # Handle text or json
    if content_type.startswith("text/") or content_type == "application/json":
        logger.debug("Processing text resource")
        return {
            "type": "text",
            "text": response.text,
            "content_type": content_type,
            "encoding": "utf-8",
        }
        
    # Handle images
    elif content_type.startswith("image/"):
        logger.debug("Processing image")
        img = PILImage.open(io.BytesIO(response.content))
        img_bytes = optimize_image(img)
        
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64.b64encode(img_bytes).decode("utf-8")
            }
        }
            
    # Handle other file types
    else:
        logger.debug("Processing binary resource")
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": content_type,
                "data": base64.b64encode(response.content).decode("utf-8"),
            },
        }
