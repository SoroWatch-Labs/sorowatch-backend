"""
API key authentication for the SoroWatch API.

Clients send the key in an `X-API-Key` header. If no API_KEY is configured
the check is skipped, so local development works without setup; set
API_KEY in any real deployment.
"""
import secrets

from fastapi import Header, HTTPException, status

from app.config import get_settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = get_settings().api_key
    if not expected:
        return  # auth disabled (development)

    # compare_digest avoids leaking the key through response-time differences.
    if x_api_key is None or not secrets.compare_digest(
        x_api_key.encode(), expected.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
