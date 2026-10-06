# sorowatch-backend

Coordination layer for SoroWatch. Reads flag events from the on-chain
contract via Soroban RPC, calls the sorowatch-ai-agent service for
scoring, and — when a responder key is configured — submits flags
on-chain using the real Stellar Python SDK.

## Endpoints

- `GET /health`
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
```

`RESPONDER_SECRET_KEY` is optional — without it, on-chain submission is
disabled but reading events and scoring still work.

`API_KEY` protects `/events` and `/risk/*`: requests must include an
`X-API-Key` header with the same value or they get `401`. `/health` stays
public. If `API_KEY` is empty, auth is disabled (handy for local
development) — always set it in a real deployment.

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
