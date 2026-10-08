"""Client for calling the sorowatch-ai-agent scoring service."""
import httpx


class AiAgentClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def score_address(self, address: str, threshold: int = 50) -> dict:
        url = f"{self.base_url}/score"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url, json={"address": address, "threshold": threshold}
            )
            response.raise_for_status()
            return response.json()

    async def is_healthy(self) -> bool:
        """True if the agent's /health answers 200; never raises."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
