from httpx._types import (
    HeaderTypes,
)
from loguru import logger
from fastmcp.server.dependencies import get_http_headers


def inject_auth_header(headers: HeaderTypes | None = None) -> HeaderTypes:
    """
    Inject JWT token from FastMCP context into headers if available.

    Args:
        headers: Existing headers dict or None

    Returns:
        Headers dict with Authorization header added if JWT is available
    """
    # Start with existing headers or empty dict
    if headers is None:
        headers = {}
    elif not isinstance(headers, dict):
        # Convert other header types to dict
        headers = dict(headers)  # type: ignore
    else:
        # Make a copy to avoid modifying the original
        headers = headers.copy()

    http_headers = get_http_headers()
    logger.debug(f"HTTP headers: {http_headers}")

    authorization = http_headers.get("Authorization") or http_headers.get("authorization")
    if authorization:
        headers["Authorization"] = authorization  # type: ignore
        logger.debug("Injected JWT token into authorization request headers")
    else:
        logger.debug("No authorization found in request headers")

    # This is a workaround for zlib decompression issues in Fly.io proxy
    #   See: https://fly.io/docs/reference/content-encoding/
    content_encoding = http_headers.get('Content-Encoding') or http_headers.get('content-encoding')
    if content_encoding:
        headers['Content-Encoding'] = 'none'  # type: ignore
        logger.debug(f"Injected Content-Encoding: {content_encoding} into request headers")

    return headers
