from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.clients.ai_agent import AiAgentClient
from app.config import get_settings

router = APIRouter()


@router.get("/health")
def health_check():
    """Liveness: the backend process is up. Does not call anything else."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness: the backend can reach the AI scoring agent it depends on.
    Returns 503 when a dependency is down so load balancers and uptime
    monitors can tell "running" from "actually usable".
    """
    settings = get_settings()
    client = AiAgentClient(settings.ai_agent_url, timeout=3.0)
    ai_agent_ok = await client.is_healthy()
    body = {
        "status": "ok" if ai_agent_ok else "degraded",
        "checks": {"ai_agent": "ok" if ai_agent_ok else "unreachable"},
    }
    return JSONResponse(body, status_code=200 if ai_agent_ok else 503)
