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
    original_dimensions = {"width": img.width, "height": img.height}
    
    if img.width > max_size or img.height > max_size:
        ratio = min(max_size / img.width, max_size / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        logger.debug("Resizing image", 
                    original=original_dimensions, 
                    target=new_size,
                    ratio=ratio)
        return img.resize(new_size, PILImage.Resampling.LANCZOS)
    
    logger.debug("No resize needed", dimensions=original_dimensions)
    return img

def optimize_image(img, max_output_bytes=500000):  # 500KB limit
    """Iteratively optimize image until it's under max_output_bytes"""
    logger.debug("Starting optimization", 
                dimensions={"width": img.width, "height": img.height}, 
                mode=img.mode,
                max_bytes=max_output_bytes)
    
    # Start with higher quality for better color preservation
    quality = 60
    
    # Make initial size relative to input dimensions
    initial_size = min(800, max(img.width, img.height))
    size = initial_size
    
    original_mode = img.mode
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        # Keep original mode info for logging
        img = img.convert('RGB')
        logger.debug("Converted color mode", 
                    from_mode=original_mode,
                    to_mode='RGB')
    
    while True:
        buf = io.BytesIO()
        resized = resize_image(img, size)
        
        resized.save(buf, format='JPEG',
                    quality=quality,
                    optimize=True,
                    progressive=True,
                    subsampling='4:2:0')
        
        output_size = buf.getbuffer().nbytes
        logger.debug("Optimization attempt", 
                    quality=quality, 
                    size=size, 
                    output_bytes=output_size,
                    target_bytes=max_output_bytes)
        
        if output_size < max_output_bytes:
            compression_ratio = output_size / max_output_bytes
            logger.info("Image optimization complete", 
                       final_size=output_size,
                       quality=quality,
                       dimensions={"width": resized.width, "height": resized.height},
                       compression_ratio=compression_ratio)
            return buf.getvalue()
            
        # More gradual quality reduction for better color preservation
        if quality > 30:
            quality_step = 5 if quality > 50 else 10
            quality -= quality_step
            logger.debug("Reducing quality", 
                        new_quality=quality,
                        step=quality_step)
        # Smaller size reduction steps
        elif size > 300:
            size_step = 25 if size > 600 else 50
            size -= size_step
            logger.debug("Reducing size", 
                        new_size=size,
                        step=size_step)
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
