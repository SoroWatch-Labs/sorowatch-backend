from fastapi import APIRouter, Query
from app.config import get_settings
from app.clients.soroban_rpc import SorobanRpcClient

router = APIRouter()


@router.get(
    "/",
    summary="List flagged events",
    responses={
        200: {
            "description": "Flagged events read live from Soroban RPC. Empty list (not an error) when CONTRACT_ID is unset or there are no events yet.",
            "content": {
                "application/json": {
                    "example": {
                        "events": [
                            {
                                "type": "contract",
                                "contractId": "CABC1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ234567890ABCDEFG",
                                "ledger": 123456,
                                "ledgerClosedAt": "2026-01-01T00:00:00Z",
                                "id": "0000000123-0000000001",
                                "topic": ["flagged"],
                                "value": "80",
                            }
                        ]
                    }
                }
            },
        }
    },
)
async def list_events(start_ledger: int = Query(default=1, ge=1)):
    """
    Return 'flagged' events emitted by the sorowatch-contract, read live
    from Soroban RPC. Returns an empty list (not an error) if the
    contract ID isn't configured yet or has no events.
    """
    settings = get_settings()
    if not settings.contract_id:
        return {"events": [], "note": "CONTRACT_ID not configured"}

    client = SorobanRpcClient(settings.soroban_rpc_url)
    events = await client.get_events(
        contract_id=settings.contract_id,
        start_ledger=start_ledger,
        topic_filter="flagged",
    )
    return {"events": events}
