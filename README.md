# sorowatch-backend

Coordination layer for SoroWatch. Reads flag events from the on-chain
contract via Soroban RPC, calls the sorowatch-ai-agent service for
scoring, and — when a responder key is configured — submits flags
on-chain using the real Stellar Python SDK.

## Endpoints

- `GET /health` — liveness; always `{"status": "ok"}` while the process is up
- `GET /health/ready` — readiness; checks the AI agent's `/health` (3 second
  timeout) and returns `503` with `{"status": "degraded"}` if it is down
- `GET /events?start_ledger=N` — reads real `flagged` events from Soroban
  RPC for the configured contract
- `POST /risk/score` — calls sorowatch-ai-agent to score an address;
  optionally submits the flag on-chain if `submit_on_chain_if_flagged`
  is true and a responder key is configured

## Configuration (.env)

```
SOROBAN_RPC_URL=https://soroban-testnet.stellar.org
NETWORK_PASSPHRASE=Test SDF Network ; September 2015
CONTRACT_ID=<deployed contract ID>
AI_AGENT_URL=http://localhost:8001
RESPONDER_SECRET_KEY=<Stellar secret key authorized as Responder on the contract>
API_KEY=<shared secret clients must send in the X-API-Key header>
RISK_RATE_LIMIT_PER_MINUTE=60
```

`RESPONDER_SECRET_KEY` is optional — without it, on-chain submission is
disabled but reading events and scoring still work.

`API_KEY` protects `/events` and `/risk/*`: requests must include an
`X-API-Key` header with the same value or they get `401`. `/health` and
`/health/ready` stay public. If `API_KEY` is empty, auth is disabled (handy for local
development) — always set it in a real deployment.

## Rate limiting

`POST /risk/score` is limited per client IP to `RISK_RATE_LIMIT_PER_MINUTE`
requests in any rolling 60 seconds (default 60; set `0` to turn it off).
Over the limit, the API answers `429` with a `Retry-After` header (seconds)
and does not call the AI agent. Requests with a bad API key are rejected
with `401` first and do not count. The limiter is in memory, so each worker
process counts separately, and behind a reverse proxy every request shows
the proxy's IP unless the proxy forwards the real client address.

## Logging

Every request is logged as one JSON line on the `sorowatch.access` logger,
for example:

```
{"event": "request", "request_id": "3f2a...", "method": "GET", "path": "/health", "status": 200, "duration_ms": 1.4, "client": "127.0.0.1"}
```

Send an `X-Request-ID` header to reuse your own trace ID; otherwise one is
generated. The ID is returned in the `X-Request-ID` response header.
Headers, query strings and bodies are never logged, so secrets like the
API key stay out of the logs.

## Run

```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Test

```
python -m pytest
```

Tests mock all external HTTP calls (Soroban RPC, the ai-agent service) via
respx, so the suite runs offline and deterministically.
